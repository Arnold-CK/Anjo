import calendar
import datetime
from typing import List

import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe


# TODO: Make the load_df function generic
def load_deposits():
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)

    pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
    deposits_sheet = pepper_workbook.worksheet("Deposits")
    deposits_df = get_as_dataframe(deposits_sheet, parse_dates=True)

    deposits_df.drop(columns=["Timestamp"], inplace=True)
    deposits_df["Date"] = pd.to_datetime(deposits_df["Date"], format="%d/%m/%y")

    result = deposits_df.dropna(how="all")

    return result


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime("%d/%b/%Y")

    return formatted_date


def process_deposit_month(deposits_df, month):
    # Ensure the Date column is in datetime format
    deposits_df["Date"] = pd.to_datetime(deposits_df["Date"], format="%d/%m/%y")

    deposits_df["Month"] = deposits_df["Date"].dt.month_name()

    # Filter the DataFrame for the given month
    filtered_df = deposits_df[deposits_df["Month"] == month]

    # Sort the filtered DataFrame by Date in descending order
    filtered_df = filtered_df.sort_values(by="Date", ascending=False)

    # Reset the index and drop the old index
    filtered_df = filtered_df.reset_index(drop=True)
    filtered_df.index += 1

    # Drop the temporary 'Month' column
    filtered_df = filtered_df.drop(columns=["Month"])
    
    # Extract year before formatting the date
    year = filtered_df["Date"].dt.year.iloc[0] if not filtered_df.empty else ""
    
    filtered_df["Date"] = filtered_df["Date"].apply(format_date)
    
    # Add year as a separate column to pass it along
    if not filtered_df.empty:
        filtered_df["_year"] = year

    return filtered_df


def display_expander(month, month_df):
    ttl_deposit = month_df["Amount"].sum()
    formatted_ttl_deposit = "{:,.0f}".format(ttl_deposit)
    
    # Get the year from the _year column, or use empty string if not available
    year = month_df["_year"].iloc[0] if not month_df.empty and "_year" in month_df.columns else ""
    
    # Remove the _year column before displaying the dataframe
    display_df = month_df.drop(columns=["_year"]) if "_year" in month_df.columns else month_df
    
    with st.expander(f"{month} {year} - Total Deposited: {formatted_ttl_deposit} UGX"):
        st.dataframe(display_df, use_container_width=True)


# TODO: Make the filters generic but ensure each page has its own filter


def filter_data(
    data: pd.DataFrame, filter_name: str, values: List[str]
) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "years":
        data = data[data["Date"].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data["Date"].dt.month.isin(values)]

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
    return data
    return data
