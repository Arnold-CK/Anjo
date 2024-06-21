import altair as alt
import gspread
import pandas as pd
import streamlit as st
from millify import millify
from streamlit_option_menu import option_menu as option_menu

import cost_functions as cfx
import general_functions as gfx
import sales_functions as sfx
import deposit_functions as dfx
import withdraw_functions as wfx
from pytz import timezone

import calendar
import datetime
from datetime import date

gfx.set_page_config()

name, authentication_status, username, authenticator = gfx.auth()

if authentication_status:

    if 'date_range_toggle' not in st.session_state:
        st.session_state["date_range_toggle"] = False

    if 'nav_bar_selection' not in st.session_state:
        st.session_state["nav_bar_selection"] = "Costs"

    if 'quantity' not in st.session_state:
        st.session_state["quantity"] = 0

    if 'unit-price' not in st.session_state:
        st.session_state["unit-price"] = 0

    # st.write(st.session_state)

    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    current_user = st.session_state["name"]


    def change_nav_bar_state_selection(selected_option: str):
        st.session_state.nav_bar = selected_option


    with st.sidebar:
        nav_bar = option_menu(
            current_user,
            ["Costs", "Sales", "Harvests", "Deposits", "Withdraws"],
            icons=["bar-chart-line", "coin", "flower3", "node-plus", "node-minus"],
            menu_icon="person-circle",
            key="nav_bar_selection",
            on_change=change_nav_bar_state_selection(st.session_state["nav_bar_selection"]),

        )

        # disable_status = st.toggle("Enable", value=True)
        # st.multiselect("Select", options=[i for i in range(10)], disabled=not disable_status)

        with st.expander("Filters", expanded=True):
            years, months, cost_categories, customers, start_date, end_date = gfx.show_filters(
                nav_bar_selection=st.session_state["nav_bar"])

            months = [k for k, v in gfx.get_month_name_dict().items() if v in months]

            if end_date and not start_date:
                st.error("Cannot have an end date without a start date")
                st.stop()

            if start_date and end_date:
                if start_date > end_date:
                    st.error("Selected start date should be less than the end date")
                    st.stop()

        st.divider()

    if nav_bar == "Costs":
        details, dashboard, costs_form = st.tabs(["📝 Details", "💰 Dashboard", "📜 Form"])

        anjo_workbook = gc.open_by_key(st.secrets["cost_sheet_key"])

        expenses_sheet = anjo_workbook.worksheet("Costs")

        expenses_df = cfx.load_expense_data(expenses_sheet)

        expenses_df = cfx.filter_data(expenses_df, 'years', years)
        expenses_df = cfx.filter_data(expenses_df, 'months', months)
        expenses_df = cfx.filter_data(expenses_df, "cost_categories", cost_categories)
        expenses_df = cfx.filter_data(expenses_df, 'start_date', start_date)
        expenses_df = cfx.filter_data(expenses_df, 'end_date', end_date)

        with details:

            if expenses_df.empty:
                st.info("No records match the filtration criteria")
                st.stop()

            st.subheader("Costs by Categories")

            df_cost_categories = expenses_df["Cost Category"].unique()
            df_cost_categories.sort()

            for category in df_cost_categories:
                category_df = cfx.process_category(expenses_df, category)
                cfx.display_expander(category, category_df)

        with dashboard:

            visuals_df = pd.DataFrame({
                "Category": expenses_df["Cost Category"],
                "Cost (ugx)": expenses_df["Total Cost"],
                "Date": expenses_df["Date"]
            })

            cost_metrics, pie_chart = st.columns([1, 2])

            with cost_metrics:
                total_costs = expenses_df["Total Cost"].sum()
                st.metric(
                    "Total Costs",
                    millify(total_costs, precision=2),
                )

                number_of_months = expenses_df['Date'].dt.month.nunique()

                average_monthly_cost = total_costs / number_of_months if number_of_months > 0 else 0

                st.metric("Average monthly Cost", millify(average_monthly_cost, precision=2))

                # st.metric("Cost per Unit", millify(total_costs, precision=2))

                # st.metric("Cost of Goods Sold", millify(total_costs, precision=2))

            with pie_chart:
                pie_chart = alt.Chart(visuals_df).mark_arc(innerRadius=80).encode(
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
                         alt.Tooltip("Category", title="Category"),
                         alt.Tooltip("sum(Cost (ugx)):Q", title="Total Cost (UGX)", format=',')
                         ]
            )

            st.altair_chart(stacked_chart, use_container_width=True)

        with costs_form:
            item_key = "txtCostItem"
            category_key = "slctCostCategory"
            amount_key = "txtCostAmount"

            with st.form(key="anjo_costs", clear_on_submit=True):
                cost_date = st.date_input("Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                          max_value=datetime.datetime.now(),
                                          min_value=datetime.date(2022, 8, 1),
                                          help="Date **MUST** be before or equal to today")

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

                            timestamp = datetime.datetime.now(timezone).strftime(
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

                            anjo_sheet = gc.open_by_key(st.secrets["cost_sheet_key"])
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

    elif nav_bar == "Sales":

        sales_details, sales_dashboard, sales_form = st.tabs(["📝 Details", "💰 Dashboard", "📜 Form"])

        final_sales_df = sfx.get_sales_df()

        # TODO:
        # Turn this into a function that takes in the df, and a dictionary of column names and values
        # Annotate all functions to clearly show the data types of the attributes plus what they return
        # Create functions to handle the costs
        # Put files in folders where need be
        # Transfer data from old sheets
        # Put all data being read by the app in one sheet

        final_sales_df = sfx.filter_data(final_sales_df, 'years', years)
        final_sales_df = sfx.filter_data(final_sales_df, 'months', months)
        final_sales_df = sfx.filter_data(final_sales_df, 'customers', customers)
        final_sales_df = sfx.filter_data(final_sales_df, 'start_date', start_date)
        final_sales_df = sfx.filter_data(final_sales_df, 'end_date', end_date)

        with sales_details:
            if final_sales_df.empty:
                st.info("No records match the filtration criteria")
                st.stop()

            st.subheader("Sales by Customers")

            df_customers = final_sales_df["Customer"].unique()
            df_customers.sort()

            for customer in df_customers:
                customer_df = sfx.process_customer(final_sales_df, customer)
                sfx.display_expander(customer, customer_df)

        with sales_dashboard:

            ttl_revenue, ttl_quantity = st.columns(2)

            with ttl_revenue:
                total_revenue = final_sales_df["Total Price"].sum()
                st.metric(
                    "Total Revenue (ugx)",
                    millify(total_revenue, precision=2),
                )

            with ttl_quantity:
                total_quantity = final_sales_df["Quantity"].sum()
                st.metric(
                    "Total Quantity Sold (kgs)",
                    millify(total_quantity, precision=2),
                )

            visuals_df = pd.DataFrame({
                "Quantity Sold (kgs)": final_sales_df["Quantity"],
                "Revenue (ugx)": final_sales_df["Total Price"],
                "Date": final_sales_df["Date"]
            })

            st.write("---")

            line = (
                alt.Chart(visuals_df)
                .mark_line()
                .encode(
                    x=alt.X("month(Date):O", title="Month"),
                    y=alt.Y("sum(Revenue (ugx)):Q", title="Total Revenue (UGX)"),
                    tooltip=[alt.Tooltip("month(Date):O", title="Month"),
                             alt.Tooltip("sum(Revenue (ugx)):Q", title="Total Revenue (UGX)", format=','),
                             ]
                )
            )

            points = line.mark_point()

            st.altair_chart(line + points, use_container_width=True)

            st.write("---")

            bar = (
                alt.Chart(visuals_df)
                .mark_bar()
                .encode(
                    x=alt.X("month(Date):O", title="Month"),
                    y=alt.Y("sum(Quantity Sold (kgs)):Q", title="Total Quantity Sold (kgs)"),
                    tooltip=[alt.Tooltip("month(Date):O", title="Month"),
                             alt.Tooltip("sum(Quantity Sold (kgs)):Q", title="Total Quantity Sold (kgs)", format=','),
                             ]
                )
            )

            st.altair_chart(bar, use_container_width=True)

        with sales_form:
            st.title(":green[Sales]")

            with st.form(key="sales", clear_on_submit=True):
                date = st.date_input("Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                     max_value=datetime.datetime.now(),
                                     min_value=datetime.date(2022, 8, 1),
                                     help="Date **MUST** be before or equal to today")

                customer = st.text_input(
                    placeholder="john doe",
                    label="Customer",
                    disabled=False
                )

                size = st.selectbox(label="Size", options=sfx.get_sizes())

                unit = st.selectbox(label="Unit", options=sfx.get_units())

                unit_price = st.text_input(
                    key="unit-price",
                    placeholder="ugx",
                    label="Unit Price",
                    disabled=False,
                    help="Please enter a value greater than zero"
                )

                quantity = st.text_input(
                    key="quantity",
                    placeholder="0",
                    label="Quantity",
                    disabled=False,
                    help="Please enter a value greater than zero"
                )

                total_price = st.text_input(
                    placeholder="ugx",
                    label="Total Price",
                    disabled=True,
                    value=int(st.session_state["quantity"]) * int(st.session_state["unit-price"])
                    if int(st.session_state["quantity"]) > 0 and
                       int(st.session_state["unit-price"]) > 0 else 0
                )

                sale_submitted = st.form_submit_button("Save")

                if sale_submitted:
                    timezone = timezone("Africa/Nairobi")

                    # amount_deposited = int(amount.strip())

                    timestamp = datetime.datetime.now(timezone).strftime(
                        "%d-%b-%Y %H:%M:%S" + " EAT"
                    )

                    data = [
                        timestamp,
                        date.strftime('%d/%m/%y'),
                        int(amount)
                    ]

                    with st.spinner("Saving deposit data..."):
                        sheet_credentials = st.secrets["sheet_credentials"]
                        gc = gspread.service_account_from_dict(sheet_credentials)

                        pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Deposits")

                        all_values = deposits_sheet.get_all_values()

                        next_row_index = len(all_values) + 1

                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )

                        st.success(
                            "✅ Deposit Saved Successfully. Feel free to close the application"
                        )

    elif nav_bar == "Deposits":
        deposits, deposit_form = st.tabs(["➕ Deposits", "📜 Form"])

        deposits_df = dfx.load_deposits()

        deposits_df = dfx.filter_data(deposits_df, 'years', years)
        deposits_df = dfx.filter_data(deposits_df, 'months', months)
        deposits_df = dfx.filter_data(deposits_df, 'start_date', start_date)
        deposits_df = dfx.filter_data(deposits_df, 'end_date', end_date)

        with deposits:

            if deposits_df.empty:
                st.info("No records match the filtration criteria")
                st.stop()

            # Extract unique months (as Period objects)
            unique_months = deposits_df['Date'].dt.month_name().unique()

            # Convert to a list of strings
            unique_months_list = unique_months.tolist()

            for month in unique_months_list:
                month_df = dfx.process_deposit_month(deposits_df, month)
                dfx.display_expander(month, month_df)

        with deposit_form:

            st.title(":green[Deposits]")

            with st.form(key="deposits", clear_on_submit=True):
                date = st.date_input("Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                     max_value=datetime.datetime.now(),
                                     min_value=datetime.date(2022, 8, 1),
                                     help="Date **MUST** be before or equal to today")

                amount = st.text_input(
                    placeholder="ugx",
                    label="Amount deposited",
                    disabled=False,
                    help="Please enter a value greater than zero"
                )

                submitted = st.form_submit_button("Save")

                if submitted:
                    timezone = timezone("Africa/Nairobi")

                    # amount_deposited = int(amount.strip())

                    timestamp = datetime.datetime.now(timezone).strftime(
                        "%d-%b-%Y %H:%M:%S" + " EAT"
                    )

                    data = [
                        timestamp,
                        date.strftime('%d/%m/%y'),
                        int(amount)
                    ]

                    with st.spinner("Saving deposit data..."):
                        sheet_credentials = st.secrets["sheet_credentials"]
                        gc = gspread.service_account_from_dict(sheet_credentials)

                        pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Deposits")

                        all_values = deposits_sheet.get_all_values()

                        next_row_index = len(all_values) + 1

                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )

                        st.success(
                            "✅ Deposit Saved Successfully. Feel free to close the application"
                        )

    elif nav_bar == "Withdraws":
        withdraws, withdraw_form = st.tabs(["➖ Withdraws", "📜 Form"])

        withdraw_df = wfx.load_withdraws()

        withdraw_df = wfx.filter_data(withdraw_df, 'years', years)
        withdraw_df = wfx.filter_data(withdraw_df, 'months', months)
        withdraw_df = wfx.filter_data(withdraw_df, 'start_date', start_date)
        withdraw_df = wfx.filter_data(withdraw_df, 'end_date', end_date)

        with withdraws:

            if withdraw_df.empty:
                st.info("No records match the filtration criteria")
                st.stop()

            # Extract unique months (as Period objects)
            unique_months = withdraw_df['Date'].dt.month_name().unique()

            # Convert to a list of strings
            unique_months_list = unique_months.tolist()

            for month in unique_months_list:
                month_df = dfx.process_deposit_month(withdraw_df, month)
                dfx.display_expander(month, month_df)

        with withdraw_form:

            st.title(":red[Withdraws]")

            with st.form(key="withdraws", clear_on_submit=True):
                date = st.date_input("Date (dd/mm/yyyy)", value=None, format="DD/MM/YYYY",
                                     max_value=datetime.datetime.now(),
                                     min_value=datetime.date(2022, 8, 1),
                                     help="Date **MUST** be before or equal to today")

                amount = st.text_input(
                    placeholder="ugx",
                    label="Amount withdrawn",
                    disabled=False,
                    help="Please enter a value greater than zero"
                )

                submitted = st.form_submit_button("Save")

                if submitted:
                    timezone = timezone("Africa/Nairobi")

                    timestamp = datetime.datetime.now(timezone).strftime(
                        "%d-%b-%Y %H:%M:%S" + " EAT"
                    )

                    data = [
                        timestamp,
                        date.strftime('%d/%b/%Y'),
                        int(amount)
                    ]

                    with st.spinner("Saving withdraw data..."):
                        sheet_credentials = st.secrets["sheet_credentials"]
                        gc = gspread.service_account_from_dict(sheet_credentials)

                        pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Withdraws")

                        all_values = deposits_sheet.get_all_values()

                        next_row_index = len(all_values) + 1

                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )

                        st.success(
                            "✅ Withdraw Saved Successfully. Feel free to close the application"
                        )

    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
