import altair as alt
import gspread
import pandas as pd
import streamlit as st
from millify import millify
from streamlit_option_menu import option_menu as option_menu

import functions as fx

fx.set_page_config()

name, authentication_status, username, authenticator = fx.auth()

if authentication_status:

    if 'date_range_toggle' not in st.session_state:
        st.session_state["date_range_toggle"] = False

    # st.write(st.session_state)

    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    current_user = st.session_state["name"]

    with st.sidebar:
        nav_bar = option_menu(
            current_user,
            ["Costs"],
            icons=["bar-chart-line"],
            menu_icon="person-circle",
        )

        # disable_status = st.toggle("Enable", value=True)
        # st.multiselect("Select", options=[i for i in range(10)], disabled=not disable_status)

        with st.expander("Filters", expanded=True):
            years, months, cost_categories, start_date, end_date = fx.show_filters()

            months = [k for k, v in fx.get_month_name_dict().items() if v in months]

            if end_date and not start_date:
                st.error("Cannot have an end date without a start date")
                st.stop()

            if start_date and end_date:
                if start_date > end_date:
                    st.error("Selected start date should be less than the end date")
                    st.stop()

        st.divider()

    if nav_bar == "Costs":
        details, dashboard = st.tabs(["📝 Details", "💰 Dashboard"])

        anjo_workbook = gc.open_by_key(st.secrets["other_sheet_key"])

        expenses_sheet = anjo_workbook.worksheet("Expenses")

        expenses_df = fx.load_expense_data(expenses_sheet)

        expenses_df = fx.filter_data(expenses_df, 'years', years)
        expenses_df = fx.filter_data(expenses_df, 'months', months)
        expenses_df = fx.filter_data(expenses_df, "cost_categories", cost_categories)
        expenses_df = fx.filter_data(expenses_df, 'start_date', start_date)
        expenses_df = fx.filter_data(expenses_df, 'end_date', end_date)

        with details:

            st.spinner("Me")

            if expenses_df.empty:
                st.info("No records match the filtration criteria")
                st.stop()

            st.subheader("Costs by Categories")

            df_cost_categories = expenses_df["data-bio_data-cost_category"].unique()
            df_cost_categories.sort()

            for category in df_cost_categories:
                category_df = fx.process_category(expenses_df, category)
                fx.display_expander(category, category_df)

        with dashboard:

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

                number_of_months = expenses_df['data-bio_data-date'].dt.month.nunique()

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

    # --- DATA ENTRY FORMS ---

    # if nav_bar == "Data Entry":
    #     entry_option = option_menu(
    #         menu_title=None,
    #         options=["Sales Form", "Costs Form"],
    #         icons=["journal-plus", "journal-minus"],
    #         orientation="horizontal",
    #     )
    #
    #     # --- SALES FORM ---
    #
    #     if entry_option == "Sales Form":
    #         st.write("Sales Form")
    #
    #     # --- COSTS FORM ---
    #
    #     if entry_option == "Costs Form":
    #         item_key = "txtCostItem"
    #         category_key = "slctCostCategory"
    #         amount_key = "txtCostAmount"
    #
    #         with st.form(key="anjo_costs", clear_on_submit=True):
    #             cost_date = st.date_input(
    #                 label="Date", value=datetime.today(), format="DD-MM-YYYY"
    #             )
    #
    #             st.write("---")
    #
    #             st.text_input(label="Item", disabled=False, key=item_key)
    #
    #             st.selectbox(
    #                 label="Category", options=cost_categories, key=category_key
    #             )
    #
    #             st.text_input(
    #                 label="Amount",
    #                 disabled=False,
    #                 key=amount_key,
    #                 placeholder="ugx",
    #             )
    #
    #             submitted = st.form_submit_button("Save")
    #
    #             if submitted:
    #                 is_valid = True
    #                 cost_date = cost_date.strftime("%d-%b-%Y")
    #
    #                 with st.spinner("🔍 Validating form..."):
    #                     item = st.session_state.get(item_key, "")
    #                     category = st.session_state.get(category_key, "")
    #                     amount = st.session_state.get(amount_key, "")
    #
    #                     if not item.strip():
    #                         is_valid = False
    #                         st.warning("⚠️ Item cannot be left blank")
    #
    #                     if not category.strip():
    #                         is_valid = False
    #                         st.warning("⚠️ Category cannot be left blank")
    #
    #                     if amount.strip():
    #                         amount = float(amount.strip())
    #                         if amount <= 0.0:
    #                             is_valid = False
    #                             st.warning("🚨 Please enter an Amount greater than zero")
    #                     else:
    #                         is_valid = False
    #                         st.warning("⚠️ Amount cannot be left blank")
    #
    #                 if is_valid:
    #                     st.info("👍 Form is Valid")
    #
    #                     with st.spinner("Saving Cost Data..."):
    #                         timezone = timezone("Africa/Nairobi")
    #
    #                         timestamp = datetime.now(timezone).strftime(
    #                             "%d-%b-%Y %H:%M:%S" + " EAT"
    #                         )
    #
    #                         data = [
    #                             cost_date,
    #                             item,
    #                             category,
    #                             amount,
    #                             current_user,
    #                             timestamp,
    #                         ]
    #
    #                         anjo_sheet = gc.open_by_key(st.secrets["sheet_key"])
    #                         worksheet = anjo_sheet.worksheet("Costs")
    #
    #                         all_values = worksheet.get_all_values()
    #
    #                         next_row_index = len(all_values) + 1
    #
    #                         worksheet.append_row(
    #                             data,
    #                             value_input_option="user_entered",
    #                             insert_data_option="insert_rows",
    #                             table_range=f"a{next_row_index}",
    #                         )
    #
    #                         st.success("✅ Cost data Saved Successfully!")
    #
    #                         # REDIRECT TO THE COSTS DASHBOARD

    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
