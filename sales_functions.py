import calendar
import datetime
from typing import List

import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe
import gspread


@st.cache_data
def get_month_name_dict():
    return {i: month_name for i, month_name in enumerate(calendar.month_name) if i != 0}


def format_column(entry):
    return ' '.join(word.capitalize() for word in entry.split('_'))


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime('%d/%b/%Y')

    return formatted_date


# def clean_sales_df(sales_df):
#     # ToDo: Investigate why there is data loss when dropNa is used
#
#     sales_df = sales_df.loc[:, ["date", "customer",
#                                 "size",
#                                 "quantity",
#                                 "unit",
#                                 "unit price",
#                                 "total price"]].dropna()
#
#     # big_sales_df = sales_df[sales_df["data-bio_data-size"] == "big"]
#     #
#     # big_sales_df = big_sales_df.loc[:, ["data-bio_data-date", "data-bio_data-customer",
#     #                                     "data-bio_data-size",
#     #                                     "data-size_big-quantity_big", "data-size_big-unit_price_big",
#     #                                     "data-size_big-total_price_big"]]
#     #
#     # small_sales_df = sales_df[sales_df["data-bio_data-size"] == "small"]
#     #
#     # small_sales_df = small_sales_df.loc[:, ["data-bio_data-date", "data-bio_data-customer",
#     #                                         "data-bio_data-size",
#     #                                         "data-size_small-quantity_small",
#     #                                         "data-size_small-unit_price_small",
#     #                                         "data-size_small-total_price_small"]]
#
#     sales_df.rename(columns={
#         "date": "Date",
#         "customer": "Customer",
#         "size": "Size",
#         "unit": "Unit",
#         "unit price": "Unit Price",
#         "quantity": "Quantity",
#         "total price": "Total Price",
#     }, inplace=True)
#
#     # big_sales_df.rename(columns={
#     #     "data-bio_data-date": "Date",
#     #     "data-bio_data-customer": "Customer",
#     #     "data-bio_data-size": "Size",
#     #     "data-size_big-quantity_big": "Quantity",
#     #     "data-size_big-unit_price_big": "Unit Price",
#     #     "data-size_big-total_price_big": "Total Price",
#     # }, inplace=True)
#
#     # final_sales_df = pd.concat([big_sales_df, small_sales_df], ignore_index=True)
#
#     sales_df['Date'] = pd.to_datetime(sales_df['Date'], format='%d/%m/%y')
#
#     return sales_df


def clean_sales_df(sales_df: pd.DataFrame) -> pd.DataFrame:
    # 1) Keep only the columns we care about (case-insensitive, robust to stray spaces)
    # Normalize incoming column names once
    sales_df.columns = sales_df.columns.str.strip().str.lower()
    needed = ["date", "customer", "size", "quantity", "unit", "unit price", "total price"]
    missing = [c for c in needed if c not in sales_df.columns]
    if missing:
        raise KeyError(f"Missing expected columns: {missing}")

    sales_df = sales_df.loc[:, needed].copy()

    # 2) Trim whitespace from all string cells
    for col in sales_df.columns:
        sales_df[col] = sales_df[col].astype(str).str.strip()

    # 3) Parse Date (supports dd/mm/yy or dd/mm/yyyy)
    # Use dayfirst=True to accept dd/mm/*
    # Errors='coerce' will set invalid dates to NaT (we’ll drop those rows later if they’re useless)
    sales_df["date"] = pd.to_datetime(sales_df["date"], dayfirst=True, errors="coerce")

    # 4) Clean numeric columns: remove commas, coerce to numbers
    def to_numeric(series: pd.Series) -> pd.Series:
        s = series.str.replace(",", "", regex=False)
        s = s.replace({"": None})  # empty strings -> NaN
        return pd.to_numeric(s, errors="coerce")

    sales_df["unit price"] = to_numeric(sales_df["unit price"])
    sales_df["quantity"]   = to_numeric(sales_df["quantity"])
    sales_df["total price"] = to_numeric(sales_df["total price"])

    # 5) Rebuild Total Price if missing but unit price and quantity are present
    # (don’t overwrite valid totals)
    need_tp = sales_df["total price"].isna() & sales_df["unit price"].notna() & sales_df["quantity"].notna()
    sales_df.loc[need_tp, "total price"] = sales_df.loc[need_tp, "unit price"] * sales_df.loc[need_tp, "quantity"]

    # 6) Drop rows that are truly empty sales lines:
    #    - No date AND (quantity is NaN or 0) AND (total price is NaN or 0)
    #    (Keeps zero-value promotional rows only if date exists.)
    def is_zero_or_nan(x):
        return (x.isna()) | (x == 0)

    empty_mask = sales_df["date"].isna() & is_zero_or_nan(sales_df["quantity"]) & is_zero_or_nan(sales_df["total price"])
    sales_df = sales_df.loc[~empty_mask].copy()

    # 7) Rename columns to your preferred casing
    sales_df.rename(columns={
        "date": "Date",
        "customer": "Customer",
        "size": "Size",
        "unit": "Unit",
        "unit price": "Unit Price",
        "quantity": "Quantity",
        "total price": "Total Price",
    }, inplace=True)

    # 8) Optional: identify rows that still have non-numeric issues (for debugging)
    # bad_rows = sales_df[sales_df[["Unit Price", "Quantity", "Total Price"]].isna().any(axis=1)]
    # st.write("Rows with unresolved numeric issues:", bad_rows)

    return sales_df






def process_customer(sales_df, customer):
    customer_df = sales_df[sales_df["Customer"] == customer]
    customer_df = customer_df.sort_values(by="Date", ascending=False)
    customer_df["Date"] = customer_df["Date"].apply(format_date)

    customer_df = customer_df.reset_index(drop=True)
    customer_df.index += 1

    return customer_df


def display_expander(customer, customer_df):
    total_qty = customer_df["Quantity"].sum()
    total_money = pd.to_numeric(customer_df["Total Price"], errors="coerce").sum()
    formatted_total_money = "{:,.0f}".format(total_money)

    with st.expander(f'{customer} - {total_qty} kg - {formatted_total_money} ugx'):
        st.dataframe(customer_df, use_container_width=True)


def filter_data(data: pd.DataFrame, filter_name: str, values: List[str]) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "years":
        data = data[data['Date'].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data['Date'].dt.month.isin(values)]

    if filter_name == "customers":
        data = data[data['Customer'].isin(values)]

    if filter_name == "start_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(date_string, "%Y-%m-%d").strftime("%d/%m/%Y")
        data = data[data['Date'] >= formatted_start_date]

    if filter_name == "end_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(date_string, "%Y-%m-%d").strftime("%d/%m/%Y")
        data = data[data['Date'] <= formatted_start_date]

    return data


def convert_date_range(date_tuple):
    converted_dates = []
    for date_str in date_tuple:
        date_object = datetime.datetime.strptime(str(date_str), '%Y-%m-%d')
        converted_date = date_object.strftime('%d/%m/%y')
        converted_dates.append(converted_date)
    return converted_dates


def get_sales_df():
    sales_df = load_sales_df()
    cleaned_sales_df = clean_sales_df(sales_df)

    return cleaned_sales_df


# def load_sales_df():
#     sheet_credentials = st.secrets["sheet_credentials"]
#     gc = gspread.service_account_from_dict(sheet_credentials)
#
#     # anjo_sales_workbook = gc.open_by_key(st.secrets["sales_sheet_key"])
#     anjo_sales_workbook = gc.open_by_url(st.secrets["sales_sheet_key"])
#     sales_sheet = anjo_sales_workbook.worksheet("Final Sales")
#     sales_df = get_as_dataframe(sales_sheet, parse_dates=True)
#
#     return sales_df

def load_sales_df():
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)

    # If using a key, use open_by_key; if a full URL, use open_by_url
    anjo_sales_workbook = gc.open_by_url(st.secrets["sales_sheet_key"])
    sales_sheet = anjo_sales_workbook.worksheet("Final Sales")

    # Pull raw; don’t rely on parse_dates here—do deterministic parsing later
    sales_df = get_as_dataframe(sales_sheet, evaluate_formulas=True, dtype=str)
    return sales_df


def get_customers():
    sales_df = load_sales_df()

    customers_df = sales_df.loc[:, ["customer"]].dropna()
    unique_customers = customers_df["customer"].unique()
    unique_customers.sort()

    return unique_customers


def get_units():
    units = [
        "kg"
    ]

    units.sort()

    return units


def get_sizes():
    sizes = [
        "big",
        "small"
    ]

    sizes.sort()

    return sizes
