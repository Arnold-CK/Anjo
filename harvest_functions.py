import calendar
import datetime
from typing import List

import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe


@st.cache_data
def get_month_name_dict():
    return {i: month_name for i, month_name in enumerate(calendar.month_name) if i != 0}


def format_column(entry):
    return " ".join(word.capitalize() for word in entry.split("_"))


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime("%d/%b/%Y")

    return formatted_date


def clean_harvests_df(repeated_harvests_df, customers_harvest_df):

    repeated_harvests_df["data-structures_repeat-size_small-quantity_small_size"] = (
        pd.to_numeric(
            repeated_harvests_df[
                "data-structures_repeat-size_small-quantity_small_size"
            ],
            errors="coerce",
        ).fillna(0)
    )

    repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"] = (
        pd.to_numeric(
            repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"],
            errors="coerce",
        ).fillna(0)
    )

    # Now you can safely sum the two columns to create the 'Quantity' column
    repeated_harvests_df["Quantity"] = (
        repeated_harvests_df["data-structures_repeat-size_small-quantity_small_size"]
        + repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"]
    )

    # Rename columns for clarity
    repeated_harvests_df.rename(
        columns={
            "data-structures_repeat-structure_name": "Structure",
            "PARENT_KEY": "InstanceID",
        },
        inplace=True,
    )

    customers_harvest_df.rename(
        columns={
            "data-bio_data-date": "Date",
            "data-bio_data-client_name": "Customer",
            "data-bio_data-entered_by": "Entered By",
            "data-meta-instanceID": "InstanceID",
        },
        inplace=True,
    )

    # Merge the two DataFrames on the 'InstanceID'
    final_df = pd.merge(customers_harvest_df, repeated_harvests_df, on="InstanceID")

    # Select the relevant columns for the final DataFrame
    final_df = final_df[
        ["Date", "Customer", "Structure", "Quantity", "Entered By"]
    ].dropna()
    final_df["Date"] = pd.to_datetime(final_df["Date"], format="%d/%m/%y")

    final_df = final_df.sort_values(by="Date", ascending=False)

    final_df["Date"] = final_df["Date"].apply(format_date)
    final_df.set_index("Date", inplace=True)

    return final_df


def process_customer(sales_df, customer):
    customer_df = sales_df[sales_df["Customer"] == customer]
    customer_df = customer_df.sort_values(by="Date", ascending=False)
    customer_df["Date"] = customer_df["Date"].apply(format_date)

    customer_df = customer_df.reset_index(drop=True)
    customer_df.index += 1

    return customer_df


def display_expander(customer, customer_df):
    total_qty = customer_df["Quantity"].sum()
    total_money = customer_df["Total Price"].sum()
    formatted_total_money = "{:,.0f}".format(total_money)

    with st.expander(f"{customer} - {total_qty} kg - {formatted_total_money} ugx"):
        st.dataframe(customer_df, use_container_width=True)


def filter_data(
    data: pd.DataFrame, filter_name: str, values: List[str]
) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "years":
        data = data[data["Date"].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data["Date"].dt.month.isin(values)]

    if filter_name == "customers":
        data = data[data["Customer"].isin(values)]

    if filter_name == "start_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(
            date_string, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
        data = data[data["Date"] >= formatted_start_date]

    if filter_name == "end_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(
            date_string, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
        data = data[data["Date"] <= formatted_start_date]

    return data


def convert_date_range(date_tuple):
    converted_dates = []
    for date_str in date_tuple:
        date_object = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
        converted_date = date_object.strftime("%d/%m/%y")
        converted_dates.append(converted_date)
    return converted_dates


def get_harvests_df():
    repeated_harvests_df, customers_harvests_df = load_harvests_df()
    final_harvests_df = clean_harvests_df(repeated_harvests_df, customers_harvests_df)

    return final_harvests_df


def load_harvests_df():
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)

    anjo_harvests_workbook = gc.open_by_url(st.secrets["harvest_sheet_key"])

    repeated_harvests_sheet = anjo_harvests_workbook.worksheet("data-structures_repeat")
    repeated_harvests_df = get_as_dataframe(repeated_harvests_sheet, parse_dates=True)

    customer_harvests_sheet = anjo_harvests_workbook.worksheet("Sheet1")
    customer_harvests_df = get_as_dataframe(customer_harvests_sheet, parse_dates=True)

    return repeated_harvests_df, customer_harvests_df


def get_units():
    units = ["kg"]

    units.sort()

    return units


def get_sizes():
    sizes = ["big", "small"]

    sizes.sort()

    return sizes
