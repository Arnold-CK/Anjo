from datetime import datetime

import altair as alt
import gspread
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from gspread_dataframe import get_as_dataframe
from millify import millify
from pytz import timezone
from streamlit_option_menu import option_menu as option_menu
from yaml.loader import SafeLoader

import functions as fx

# --- PAGE CONFIG ---

st.set_page_config(page_title="Anjo Farms", page_icon="🫑", layout="wide")

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
            ["Costs", "Data Entry"],
            icons=["bar-chart-line", "clipboard-data"],
            menu_icon="person-circle",
        )

    # --- DASHBOARDS ---

    if nav_bar == "Costs":
        details, dashboard = st.tabs(["📝 Details", "💰 Dashboard"])

        anjo_workbook = gc.open_by_key(st.secrets["other_sheet_key"])

        expenses_sheet = anjo_workbook.worksheet("Expenses")

        expenses_df = get_as_dataframe(expenses_sheet, parse_dates=True)

        expenses_df = expenses_df.loc[:, ["data-bio_data-date", "data-bio_data-item",
                                          "data-bio_data-cost_category",
                                          "data-bio_data-total_cost", ]].dropna()

        expenses_df["data-bio_data-cost_category"] = expenses_df["data-bio_data-cost_category"].apply(
            fx.format_column)

        expenses_df['data-bio_data-date'] = pd.to_datetime(expenses_df['data-bio_data-date'], format='%d/%m/%y')

        with details:

            st.subheader("Costs by Categories")

            df_cost_categories = expenses_df["data-bio_data-cost_category"].unique()
            df_cost_categories.sort()

            for category in df_cost_categories:
                category_df = expenses_df[expenses_df["data-bio_data-cost_category"] == category]

                category_df = category_df.sort_values(
                    by="data-bio_data-date", ascending=False
                )

                category_df["data-bio_data-date"] = category_df["data-bio_data-date"].apply(fx.format_date)

                category_df.rename(columns={
                    "data-bio_data-date": "Date",
                    "data-bio_data-item": "Item",
                    "data-bio_data-cost_category": "Cost Category",
                    "data-bio_data-total_cost": "Total Cost",
                }, inplace=True)

                category_df = category_df.reset_index(drop=True)
                category_df.index += 1

                line_items = len(category_df)
                total_cost = category_df["Total Cost"].sum()
                formatted_total_cost = "{:,.0f}".format(total_cost)

                with st.expander(f'{category} - {line_items} line items - {formatted_total_cost} ugx'):
                    st.dataframe(category_df, use_container_width=True)

        with dashboard:

            # monthly_costs_df = expenses_df.groupby(expenses_df['data-bio_data-date'].dt.strftime('%m'))[
            #     'data-bio_data-total_cost'].sum().reset_index()
            #
            # monthly_costs_df.columns = ['Month', 'Total Cost']

            visuals_df = pd.DataFrame({
                "Category": expenses_df["data-bio_data-cost_category"],
                "Cost (ugx)": expenses_df["data-bio_data-total_cost"],
                "Date": expenses_df["data-bio_data-date"]
            })

            cost_metrics, pie_chart = st.columns([1, 2])

            with cost_metrics:
                total_costs = expenses_df["data-bio_data-total_cost"].sum()
                st.metric(
                    "Total Costs",
                    millify(total_costs, precision=2),
                )

                st.metric("Average monthly Cost", millify(total_costs, precision=2))

                st.metric("Cost per Unit", millify(total_costs, precision=2))

                st.metric("Cost of Goods Sold", millify(total_costs, precision=2))

                # total_cost_per_category = expenses_df.groupby("data-bio_data-cost_category")[
                #     "data-bio_data-total_cost"].sum()
                # category_with_largest_total = total_cost_per_category.idxmax()
                # st.metric("Average Monthly Cost", category_with_largest_total)



            with pie_chart:
                pie_chart = alt.Chart(visuals_df).mark_arc().encode(
                    theta="sum(Cost (ugx))",
                    color="Category",
                    tooltip=[alt.Tooltip("Category", title="Category"),
                             alt.Tooltip("sum(Cost (ugx))", title="Total Cost (UGX)", format=','),
                             ]
                )

                st.altair_chart(pie_chart, use_container_width=True)

            st.write("---")

            line = (
                alt.Chart(visuals_df)
                .mark_line()
                .encode(
                    x=alt.X("month(Date):O", title="Month"),
                    y=alt.Y("sum(Cost (ugx)):Q", title="Total Cost (UGX)"),
                    tooltip=[alt.Tooltip("month(Date):O", title="Month"),
                             alt.Tooltip("sum(Cost (ugx)):Q", title="Total Cost (UGX)", format=','),
                             ]
                )
            )

            points = line.mark_point()

            st.altair_chart(line + points, use_container_width=True)

            stacked_chart = alt.Chart(visuals_df).mark_bar().encode(
                x=alt.X("month(Date):O", title="Month"),
                y=alt.Y("sum(Cost (ugx)):Q", title="Total Cost (UGX)"),
                color=alt.Color("Category:N"),
                tooltip=[alt.Tooltip("month(Date):O", title="Month"),
                         alt.Tooltip("sum(Cost (ugx)):Q", title="Total Cost (UGX)", format=',')]
            )

            st.altair_chart(stacked_chart, use_container_width=True)

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
                            st.warning("⚠️ Item cannot be left blank")

                        if not category.strip():
                            is_valid = False
                            st.warning("⚠️ Category cannot be left blank")

                        if amount.strip():
                            amount = float(amount.strip())
                            if amount <= 0.0:
                                is_valid = False
                                st.warning("🚨 Please enter an Amount greater than zero")
                        else:
                            is_valid = False
                            st.warning("⚠️ Amount cannot be left blank")

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
