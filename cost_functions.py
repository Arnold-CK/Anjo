import datetime
from typing import List

import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe

import general_functions as gfx


def get_cost_categories():
    categories = [
        "Airtime & Data",
        "Construction",
        "Delivery To Customer",
        "Employee Benefits",
        "Fertilisers & Nutrients",
        "Maintenance & Repair",
        "Miscellaneous",
        "Rent & Lease",
        "Seeds & Seedlings",
        "Tools & Equipment",
        "Transport For Operations",
        "Wages & Salaries",
        "Yaka",
        "Supplies & Materials"
    ]

    categories.sort()

    return categories


def format_column(entry):
    return ' '.join(word.capitalize() for word in entry.split('_'))


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime('%d/%b/%Y')

    return formatted_date


def load_expense_data(expenses_sheet):
    expenses_df = get_as_dataframe(expenses_sheet, parse_dates=True)

    expenses_df = expenses_df.loc[:, ["data-bio_data-date", "data-bio_data-item",
                                      "data-bio_data-cost_category",
                                      "data-bio_data-total_cost", ]].dropna()

    expenses_df.rename(columns={
        "data-bio_data-date": "Date",
        "data-bio_data-item": "Item",
        "data-bio_data-cost_category": "Cost Category",
        "data-bio_data-total_cost": "Total Cost",
    }, inplace=True)

    expenses_df["Cost Category"] = expenses_df["Cost Category"].apply(
        format_column)

    expenses_df['Date'] = pd.to_datetime(expenses_df['Date'], format='%d/%m/%y')

    return expenses_df


def process_category(expenses_df, category):
    category_df = expenses_df[expenses_df["Cost Category"] == category]
    category_df = category_df.sort_values(by="Date", ascending=False)
    category_df["Date"] = category_df["Date"].apply(format_date)

    category_df = category_df.reset_index(drop=True)
    category_df.index += 1

    return category_df


def display_expander(category, category_df):
    line_items = len(category_df)
    total_cost = category_df["Total Cost"].sum()
    formatted_total_cost = "{:,.0f}".format(total_cost)

    line_item_string = "line items" if line_items > 1 else "line item"

    with st.expander(f'{category} - {line_items} {line_item_string} - {formatted_total_cost} ugx'):
        st.dataframe(category_df, use_container_width=True)


def filter_data(data: pd.DataFrame, filter_name: str, values: List[str]) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "cost_categories":
        data = data[data["Cost Category"].isin(values)]

    if filter_name == "years":
        data = data[data['Date'].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data['Date'].dt.month.isin(values)]

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
