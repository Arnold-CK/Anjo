import json
from datetime import datetime

import gspread
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from pytz import timezone
from streamlit_option_menu import option_menu as option_menu
from yaml.loader import SafeLoader

import functions as fx

# --- PAGE CONFIG ---

st.set_page_config(page_title="Anjo Farms", page_icon="🫑", layout="centered")

# --- USER AUTHENTICATION ---

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

if authentication_status:
    # --- GET DATA & SETUP---

    cost_categories = fx.get_cost_categories()
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    current_user = st.session_state["name"]

    # --- NAVIGATION BAR ---

    with st.sidebar:
        nav_bar = option_menu(
            current_user,
            ["Dashboard", "Data Entry"],
            icons=["bar-chart-line", "clipboard-data"],
            menu_icon="person-circle",
        )

    # --- DASHBOARDS ---

    if nav_bar == "Dashboard":
        sales, costs = st.tabs(["🪙 Sales Analysis", "📝 Costs Analysis"])
        with sales:
            st.write("Sales dashboard")
        with costs:
            st.write("Costs dashboard")

    # --- DATA ENTRY FORMS ---

    if nav_bar == "Data Entry":
        entry_option = option_menu(
            menu_title=None,
            options=["Sales Form", "Costs Form"],
            icons=["journal-plus", "journal-minus"],
            orientation="horizontal",
        )

        # --- SALES FORM ---

        if entry_option == "Sales Form":
            st.write("Sales Form")

        # --- COSTS FORM ---

        if entry_option == "Costs Form":
            item_key = "txtCostItem"
            category_key = "slctCostCategory"
            amount_key = "txtCostAmount"

            with st.form(key="anjo_costs", clear_on_submit=True):
                cost_date = st.date_input(
                    label="Date", value=datetime.today(), format="DD-MM-YYYY"
                )

                st.write("---")

                st.text_input(label="Item", disabled=False, key=item_key)

                st.selectbox(
                    label="Category", options=cost_categories, key=category_key
                )

                st.text_input(
                    label="Amount",
                    disabled=False,
                    key=amount_key,
                    placeholder="ugx",
                )

                submitted = st.form_submit_button("Save")

                if submitted:
                    is_valid = True
                    cost_date = cost_date.strftime("%d-%b-%Y")

                    with st.spinner("🔍 Validating form..."):
                        item = st.session_state.get(item_key, "")
                        category = st.session_state.get(category_key, "")
                        amount = st.session_state.get(amount_key, "")

                        if not item.strip():
                            is_valid = False
                            st.error("⚠️ Item cannot be left blank")

                        if not category.strip():
                            is_valid = False
                            st.error("⚠️ Category cannot be left blank")

                        if amount.strip():
                            amount = float(amount.strip())
                            if amount <= 0.0:
                                is_valid = False
                                st.error("🚨 Please enter an Amount greater than zero")
                        else:
                            is_valid = False
                            st.error("⚠️ Amount cannot be left blank")

                    if is_valid:
                        st.info("👍 Form is Valid")

                        with st.spinner("Saving Cost Data..."):
                            timezone = timezone("Africa/Nairobi")

                            timestamp = datetime.now(timezone).strftime(
                                "%d-%b-%Y %H:%M:%S" + " EAT"
                            )

                            data = [
                                cost_date,
                                item,
                                category,
                                amount,
                                current_user,
                                timestamp,
                            ]

                            anjo_sheet = gc.open_by_key(st.secrets["sheet_key"])
                            worksheet = anjo_sheet.worksheet("Costs")

                            all_values = worksheet.get_all_values()

                            next_row_index = len(all_values) + 1

                            worksheet.append_row(
                                data,
                                value_input_option="user_entered",
                                insert_data_option="insert_rows",
                                table_range=f"a{next_row_index}",
                            )

                            st.success("✅ Cost data Saved Successfully!")

                            # REDIRECT TO THE COSTS DASHBOARD

    # --- LOGOUT ---

    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
