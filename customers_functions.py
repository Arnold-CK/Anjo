import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe

def load_customers():
    # 1) auth & open sheet
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
    customers_sheet = pepper_workbook.worksheet("Customers")

    # 2) pull into DataFrame
    customers_df = get_as_dataframe(customers_sheet, parse_dates=True)

    # 3) drop rows where 'name' is missing
    df = customers_df.dropna(subset=["Name"])

    # 4) extract the 'name' column, strip whitespace, get uniques
    names = (
        df["Name"]
        .astype(str)           # ensure strings
        .str.strip()           # trim leading/trailing spaces
        .unique()              # de-duplicate
        .tolist()              # to list
    )

    # 5) sort alphabetically, case-insensitive
    names.sort(key=str.casefold)

    return names
