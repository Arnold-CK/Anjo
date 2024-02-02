import calendar
import datetime
from typing import List

import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe

import general_functions as gfx


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


def load_sales_data(sales_sheet):
    sales_df = get_as_dataframe(sales_sheet, parse_dates=True)

    sales_df = sales_df.loc[:, ["data-bio_data-date", "data-bio_data-customer",
                                "data-bio_data-size",
                                "data-size_small-quantity_small",
                                "data-size_small-unit_price_small",
                                "data-size_small-total_price_small",
                                "data-size_big-quantity_big", "data-size_big-unit_price_big",
                                "data-size_big-total_price_big"]].dropna()

    big_sales_df = sales_df[sales_df["data-bio_data-size"] == "big"]

    big_sales_df = big_sales_df.loc[:, ["data-bio_data-date", "data-bio_data-customer",
                                        "data-bio_data-size",
                                        "data-size_big-quantity_big", "data-size_big-unit_price_big",
                                        "data-size_big-total_price_big"]]

    small_sales_df = sales_df[sales_df["data-bio_data-size"] == "small"]

    small_sales_df = small_sales_df.loc[:, ["data-bio_data-date", "data-bio_data-customer",
                                            "data-bio_data-size",
                                            "data-size_small-quantity_small",
                                            "data-size_small-unit_price_small",
                                            "data-size_small-total_price_small"]]

    small_sales_df.rename(columns={
        "data-bio_data-date": "Date",
        "data-bio_data-customer": "Customer",
        "data-bio_data-size": "Size",
        "data-size_small-quantity_small": "Quantity",
        "data-size_small-unit_price_small": "Unit Price",
        "data-size_small-total_price_small": "Total Price",
    }, inplace=True)

    big_sales_df.rename(columns={
        "data-bio_data-date": "Date",
        "data-bio_data-customer": "Customer",
        "data-bio_data-size": "Size",
        "data-size_big-quantity_big": "Quantity",
        "data-size_big-unit_price_big": "Unit Price",
        "data-size_big-total_price_big": "Total Price",
    }, inplace=True)

    final_sales_df = pd.concat([big_sales_df, small_sales_df], ignore_index=True)

    final_sales_df['Date'] = pd.to_datetime(final_sales_df['Date'], format='%d/%m/%y')

    return final_sales_df


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

    with st.expander(f'{customer} - {total_qty} kg - {formatted_total_money} ugx'):
        st.dataframe(customer_df, use_container_width=True)


def filter_data(data: pd.DataFrame, filter_name: str, values: List[str]) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "years":
        data = data[data['Date'].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data['Date'].dt.month.isin(values)]

    return data


def show_filters():
    years = st.multiselect("Select Years", gfx.get_years_since_2022(),
                           placeholder="You can choose multiple options",
                           default=datetime.datetime.now().year if st.session_state.date_range_toggle is False else None,
                           disabled=st.session_state.date_range_toggle)

    months = st.multiselect("Select Months", get_month_name_dict().values(),
                            placeholder="You can choose multiple options",
                            default=None,
                            disabled=st.session_state.date_range_toggle)

    def reset_years_and_months():
        st.session_state.date_range_toggle = not st.session_state.date_range_toggle

    filter_by_date_range = st.toggle("Filter by date range", value=st.session_state.date_range_toggle,
                                     on_change=reset_years_and_months)

    if filter_by_date_range:
        def set_toggle_to_true():
            st.session_state.date_range_toggle = True

        start_date = st.date_input("Start Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                   max_value=datetime.datetime.now(),
                                   min_value=datetime.date(2022, 8, 1),
                                   help="Start Date **MUST** be less than/equal to End Date",
                                   on_change=set_toggle_to_true)

        end_date = st.date_input("End Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                 max_value=datetime.datetime.now(),
                                 min_value=datetime.date(2022, 8, 1),
                                 help="End Date **MUST** be greater than/equal to Start Date",
                                 on_change=set_toggle_to_true)

        return years, months, start_date, end_date

    return years, months, None, None


def convert_date_range(date_tuple):
    converted_dates = []
    for date_str in date_tuple:
        date_object = datetime.datetime.strptime(str(date_str), '%Y-%m-%d')
        converted_date = date_object.strftime('%d/%m/%y')
        converted_dates.append(converted_date)
    return converted_dates
