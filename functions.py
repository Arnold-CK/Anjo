import calendar
from datetime import date
from typing import List
import datetime

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from gspread_dataframe import get_as_dataframe
from yaml.loader import SafeLoader


def switch_page(page_name: str):
    from streamlit.runtime.scriptrunner import RerunData, RerunException
    from streamlit.source_util import get_pages

    def standardize_name(name: str) -> str:
        return name.lower().replace("_", " ")

    page_name = standardize_name(page_name)

    pages = get_pages("Home.py")  # OR whatever your main page is called

    for page_hash, config in pages.items():
        if standardize_name(config["page_name"]) == page_name:
            raise RerunException(
                RerunData(
                    page_script_hash=page_hash,
                    page_name=page_name,
                )
            )

    page_names = [standardize_name(config["page_name"]) for config in pages.values()]

    raise ValueError(f"Could not find page {page_name}. Must be one of {page_names}")


def get_cost_categories():
    categories = [
        "Seeds And Seedlings",
        "Fertilisers And Nutrients",
        "Labour And Salaries",
        "Rent And Lease",
        "Delivery",
        "Maintenance And Repair",
        "Miscellaneous",
        "Utilities",
        "Giveaway Cost",
        "Construction"
    ]

    categories.sort()

    return categories


def get_years_since_2022():
    current_year = date.today().year
    year_list = list(range(2022, current_year + 1))
    year_list.sort(reverse=True)
    return year_list


# @st.cache_data
# def get_all_months():
#     # return list(calendar.month_name)[1:]
#     return list(range(1, 13))

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


def set_page_config():
    st.set_page_config(page_title="Anjo Farms", page_icon="🫑", layout="wide")


def auth():
    with open("./config.yaml") as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    name, authentication_status, username = authenticator.login("Login", "main")

    return name, authentication_status, username, authenticator


def load_expense_data(expenses_sheet):
    expenses_df = get_as_dataframe(expenses_sheet, parse_dates=True)

    expenses_df = expenses_df.loc[:, ["data-bio_data-date", "data-bio_data-item",
                                      "data-bio_data-cost_category",
                                      "data-bio_data-total_cost", ]].dropna()

    expenses_df["data-bio_data-cost_category"] = expenses_df["data-bio_data-cost_category"].apply(
        format_column)

    expenses_df['data-bio_data-date'] = pd.to_datetime(expenses_df['data-bio_data-date'], format='%d/%m/%y')

    return expenses_df


def process_category(expenses_df, category):
    category_df = expenses_df[expenses_df["data-bio_data-cost_category"] == category]
    category_df = category_df.sort_values(by="data-bio_data-date", ascending=False)
    category_df["data-bio_data-date"] = category_df["data-bio_data-date"].apply(format_date)

    category_df.rename(columns={
        "data-bio_data-date": "Date",
        "data-bio_data-item": "Item",
        "data-bio_data-cost_category": "Cost Category",
        "data-bio_data-total_cost": "Total Cost",
    }, inplace=True)

    category_df = category_df.reset_index(drop=True)
    category_df.index += 1

    return category_df


def display_expander(category, category_df):
    line_items = len(category_df)
    total_cost = category_df["Total Cost"].sum()
    formatted_total_cost = "{:,.0f}".format(total_cost)

    with st.expander(f'{category} - {line_items} line items - {formatted_total_cost} ugx'):
        st.dataframe(category_df, use_container_width=True)


def filter_data(data: pd.DataFrame, filter_name: str, values: List[str]) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "cost_categories":
        data = data[data["data-bio_data-cost_category"].isin(values)]

    if filter_name == "years":
        data = data[data['data-bio_data-date'].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data['data-bio_data-date'].dt.month.isin(values)]

    if filter_name == "start_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(date_string, "%Y-%m-%d").strftime("%d/%m/%Y")
        data = data[data['data-bio_data-date'] >= formatted_start_date]

    if filter_name == "end_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(date_string, "%Y-%m-%d").strftime("%d/%m/%Y")
        data = data[data['data-bio_data-date'] <= formatted_start_date]

    return data


def show_filters():
    if 'date_range_toggle' not in st.session_state:
        st.session_state.date_range_toggle = False

    years = st.multiselect("Select Years", get_years_since_2022(),
                           placeholder="You can choose multiple options",
                           default=datetime.datetime.now().year if st.session_state.date_range_toggle is False else None,
                           disabled=st.session_state.date_range_toggle)

    months = st.multiselect("Select Months", get_month_name_dict().values(),
                            placeholder="You can choose multiple options",
                            default=None,
                            disabled=st.session_state.date_range_toggle)

    cost_categories = st.multiselect("Select Categories", get_cost_categories(),
                                     placeholder="You can choose multiple options")

    filter_by_date_range = st.toggle("Filter by date range", value=st.session_state.date_range_toggle,
                                     on_change=reset_years_and_months())

    if filter_by_date_range:
        start_date = st.date_input("Start Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                   max_value=datetime.datetime.now(),
                                   min_value=datetime.date(2022, 8, 1),
                                   help="Start Date **MUST** be less than/equal to End Date")

        end_date = st.date_input("End Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                 max_value=datetime.datetime.now(),
                                 min_value=datetime.date(2022, 8, 1),
                                 help="End Date **MUST** be greater than/equal to Start Date")

        return years, months, cost_categories, start_date, end_date

    return years, months, cost_categories, None, None


def convert_date_range(date_tuple):
    converted_dates = []
    for date_str in date_tuple:
        date_object = datetime.datetime.strptime(str(date_str), '%Y-%m-%d')
        converted_date = date_object.strftime('%d/%m/%y')
        converted_dates.append(converted_date)
    return converted_dates


def reset_years_and_months():
    st.session_state.date_range_toggle = not st.session_state.date_range_toggle
