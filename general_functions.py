import calendar
import datetime
from datetime import date

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

import cost_functions as cfx
import sales_functions as sfx


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


def get_years_since_2022():
    current_year = date.today().year
    year_list = list(range(2022, current_year + 1))
    year_list.sort(reverse=True)
    return year_list


@st.cache_data
def get_month_name_dict():
    return {i: month_name for i, month_name in enumerate(calendar.month_name) if i != 0}


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


def show_filters(nav_bar_selection: str):
    years = st.multiselect("Select Years", get_years_since_2022(),
                           placeholder="You can choose multiple options",
                           default=datetime.datetime.now().year if st.session_state.date_range_toggle is False else None,
                           disabled=st.session_state.date_range_toggle)

    months = st.multiselect("Select Months", get_month_name_dict().values(),
                            placeholder="You can choose multiple options",
                            default=None,
                            disabled=st.session_state.date_range_toggle)

    cost_categories = None

    customers = None

    if nav_bar_selection == "Costs":
        cost_categories = st.multiselect("Select Categories", cfx.get_cost_categories(),
                                         placeholder="You can choose multiple options")

    if nav_bar_selection == "Sales":
        unique_customers = sfx.get_customers()
        customers = st.multiselect("Select Customers", unique_customers,
                                   placeholder="You can choose multiple options")

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

        return years, months, cost_categories, customers, start_date, end_date

    return years, months, cost_categories, customers, None, None


def tryv(me:str):
    p = [].append(me)
    hashed_passwords = stauth.Hasher(p).generate()
    return hashed_passwords

# x = tryv("vicky123")
# print(x)
