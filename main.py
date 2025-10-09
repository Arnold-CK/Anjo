import datetime

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from millify import millify
from pytz import timezone as tz
from streamlit_option_menu import option_menu

import cost_functions as cfx
import customers_functions as cusfx
import deposit_functions as dfx
import general_functions as gfx
import sales_functions as sfx
import withdraw_functions as wfx
import harvest_functions as hfx

# ---- Page & Auth ----
gfx.set_page_config()

name, authentication_status, username, authenticator = gfx.auth()

if authentication_status:

    # ---- Session State Defaults ----
    if "date_range_toggle" not in st.session_state:
        st.session_state["date_range_toggle"] = False

    if "nav_bar_selection" not in st.session_state:
        st.session_state["nav_bar_selection"] = "Costs"

    if "nav_bar" not in st.session_state:
        st.session_state["nav_bar"] = "Costs"

    if "quantity" not in st.session_state:
        st.session_state["quantity"] = 0

    if "unit-price" not in st.session_state:
        st.session_state["unit-price"] = 0

    if "total-price" not in st.session_state:
        st.session_state["total-price"] = 0

    # ---- Helpers ----
    def calculate_total_price():
        """Safely compute Quantity * Unit Price from session_state (handles blanks/commas)."""
        try:
            q = str(st.session_state.get("quantity", 0)).replace(",", "").strip()
            p = str(st.session_state.get("unit-price", 0)).replace(",", "").strip()
            q = int(float(q)) if q else 0
            p = int(float(p)) if p else 0
            total = q * p
        except Exception:
            total = 0
        st.session_state["total-price"] = total
        return total

    # Secrets / Sheets client
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    current_user = st.session_state["name"]

    # ---- Sidebar ----

    with st.sidebar:
        # keep your lists
        options = ["Costs", "Sales", "Harvests", "Deposits", "Withdraws"]
        icons = ["bar-chart-line", "coin", "flower3", "node-plus", "node-minus"]

        # pick default index from session_state (safe fallback to 0)
        default_index = options.index(st.session_state["nav_bar_selection"]) \
            if st.session_state.get("nav_bar_selection") in options else 0

        # ✅ Correct usage: menu_title is the 1st positional arg; no `key`, no `title=`
        nav_bar = option_menu(
            current_user,  # menu_title
            options,  # options
            icons=icons,  # optional
            menu_icon="person-circle",
            default_index=default_index,
            # orientation="vertical"  # (optional) default is vertical in sidebar
        )

        # mirror into session_state so rest of your code reads a single source of truth
        st.session_state["nav_bar_selection"] = nav_bar
        st.session_state["nav_bar"] = nav_bar

        with st.expander("Filters", expanded=True):
            years, months, cost_categories, customers, start_date, end_date = gfx.show_filters(
                nav_bar_selection=st.session_state["nav_bar"]
            )
            months = [k for k, v in gfx.get_month_name_dict().items() if v in months]

            if end_date and not start_date:
                st.error("Cannot have an end date without a start date")
                st.stop()
            if start_date and end_date and start_date > end_date:
                st.error("Selected start date should be less than the end date")
                st.stop()

        st.divider()

    # ===================== COSTS =====================
    if nav_bar == "Costs":
        details, dashboard, costs_form = st.tabs(["📝 Details", "💰 Dashboard", "📜 Form"])

        anjo_workbook = gc.open_by_key(st.secrets["cost_sheet_key"])
        expenses_sheet = anjo_workbook.worksheet("Costs")
        expenses_df = cfx.load_expense_data(expenses_sheet)

        expenses_df = cfx.filter_data(expenses_df, "years", years)
        expenses_df = cfx.filter_data(expenses_df, "months", months)
        expenses_df = cfx.filter_data(expenses_df, "cost_categories", cost_categories)
        expenses_df = cfx.filter_data(expenses_df, "start_date", start_date)
        expenses_df = cfx.filter_data(expenses_df, "end_date", end_date)

        if current_user != "Victor Tindimwebwa":
            with details:
                if expenses_df.empty:
                    st.info("No records match the filtration criteria")
                st.subheader("Costs by Categories")
                df_cost_categories = expenses_df["Cost Category"].dropna().unique()
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
                    total_costs = float(visuals_df["Cost (ugx)"].sum()) if not visuals_df.empty else 0.0
                    st.metric("Total Costs", millify(total_costs, precision=2))
                    number_of_months = visuals_df["Date"].dt.month.nunique() if not visuals_df.empty else 0
                    average_monthly_cost = total_costs / number_of_months if number_of_months > 0 else 0
                    st.metric("Average monthly Cost", millify(average_monthly_cost, precision=2))

                with pie_chart:
                    pie = (
                        alt.Chart(visuals_df)
                        .mark_arc(innerRadius=80)
                        .encode(
                            theta="sum(Cost (ugx))",
                            color="Category",
                            tooltip=[
                                alt.Tooltip("Category", title="Category"),
                                alt.Tooltip("sum(Cost (ugx))", title="Total Cost (UGX)", format=","),
                            ],
                        )
                    )
                    st.altair_chart(pie, use_container_width=True)

                st.write("---")

                line = (
                    alt.Chart(visuals_df)
                    .mark_line()
                    .encode(
                        x=alt.X("month(Date):O", title="Month"),
                        y=alt.Y("sum(Cost (ugx)):Q", title="Total Cost (UGX)"),
                        tooltip=[
                            alt.Tooltip("month(Date):O", title="Month"),
                            alt.Tooltip("sum(Cost (ugx)):Q", title="Total Cost (UGX)", format=","),
                        ],
                    )
                )
                points = line.mark_point()
                st.altair_chart(line + points, use_container_width=True)

                stacked = (
                    alt.Chart(visuals_df)
                    .mark_bar()
                    .encode(
                        x=alt.X("month(Date):O", title="Month"),
                        y=alt.Y("sum(Cost (ugx)):Q", title="Total Cost (UGX)"),
                        color=alt.Color("Category:N"),
                        tooltip=[
                            alt.Tooltip("month(Date):O", title="Month"),
                            alt.Tooltip("Category", title="Category"),
                            alt.Tooltip("sum(Cost (ugx)):Q", title="Total Cost (UGX)", format=","),
                        ],
                    )
                )
                st.altair_chart(stacked, use_container_width=True)

        with costs_form:
            st.title(":red[Costs]")

            with st.form(key="costs"):
                c1, c2 = st.columns(2)
                c3, c4 = st.columns(2)
                c5, c6 = st.columns(2)
                c7, c8 = st.columns(2)

                with c1:
                    date = st.date_input(
                        "Date (dd/mm/yyyy)",
                        value=datetime.datetime.now(),
                        format="DD/MM/YYYY",
                        max_value=datetime.datetime.now(),
                        min_value=datetime.date(2022, 8, 1),
                    )
                with c2:
                    category = st.selectbox(label="Category", index=None, options=cfx.get_cost_categories())
                with c3:
                    item = st.text_input(placeholder="airtime", label="Item")
                with c4:
                    cost_quantity = st.text_input(label="Quantity")
                with c5:
                    unit_cost = st.text_input(key="unit-cost", placeholder="ugx", label="Unit Cost")
                with c6:
                    total_cost = st.text_input(placeholder="ugx", label="Total Cost")
                with c7:
                    transport_cost = st.text_input(placeholder="ugx", label="Transport Cost (if any)")
                with c8:
                    transport_details = st.text_input(
                        placeholder="eg: from seeta to farm", label="Transport Details (if any)"
                    )

                source_of_funds = st.selectbox(
                    "Source of Money",
                    ["Bank", "Personal", "Sales"] if current_user in {"Andrew", "Tony"} else ["Bank", "Sales"],
                )

                cost_submitted = st.form_submit_button("Save")

                if cost_submitted:
                    tz_eat = tz("Africa/Nairobi")
                    timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")

                    data = [
                        timestamp,
                        date.strftime("%d/%m/%y"),
                        item,
                        category,
                        "",
                        cost_quantity,
                        "",
                        unit_cost,
                        total_cost,
                        transport_cost,
                        transport_details,
                        source_of_funds,
                        current_user,
                    ]

                    with st.spinner("Saving cost data..."):
                        pepper_workbook = gc.open_by_key(st.secrets["cost_sheet_key"])
                        costs_sheet = pepper_workbook.worksheet("Costs")
                        next_row_index = len(costs_sheet.get_all_values()) + 1
                        costs_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )
                        st.success("✅ Cost saved Successfully")

    # ===================== SALES =====================
    elif nav_bar == "Sales":
        customers_list = cusfx.load_customers()
        sales_details, sales_dashboard, sales_form = st.tabs(["📝 Details", "💰 Dashboard", "📜 Form"])

        final_sales_df = sfx.get_sales_df()
        final_sales_df = sfx.filter_data(final_sales_df, "years", years)
        final_sales_df = sfx.filter_data(final_sales_df, "months", months)
        final_sales_df = sfx.filter_data(final_sales_df, "customers", customers)
        final_sales_df = sfx.filter_data(final_sales_df, "start_date", start_date)
        final_sales_df = sfx.filter_data(final_sales_df, "end_date", end_date)

        if current_user != "Victor Tindimwebwa":
            with sales_details:
                if final_sales_df.empty:
                    st.info("No records match the filtration criteria")
                st.subheader("Sales by Customers")
                df_customers = final_sales_df["Customer"].dropna().unique()
                df_customers.sort()
                for customer in df_customers:
                    customer_df = sfx.process_customer(final_sales_df, customer)
                    sfx.display_expander(customer, customer_df)

            chart_color = "#D4A017"
            with sales_dashboard:
                # KPIs
                ttl_revenue, avg_sale_price, ttl_quantity, avg_order_qty = st.columns(4)
                with ttl_revenue:
                    total_revenue = float(final_sales_df["Total Price"].sum()) if not final_sales_df.empty else 0.0
                    st.metric("Total Sales (UGX)", f"{total_revenue:,.0f}")
                with avg_sale_price:
                    avg_sale_price_val = float(final_sales_df["Unit Price"].mean()) if not final_sales_df.empty else 0.0
                    st.metric("Average Sale Price", f"{avg_sale_price_val:,.0f} UGX")
                with ttl_quantity:
                    total_quantity = float(final_sales_df["Quantity"].sum()) if not final_sales_df.empty else 0.0
                    st.metric("Quantity Sold", f"{total_quantity:,.0f} kgs")
                with avg_order_qty:
                    avg_quantity = float(final_sales_df["Quantity"].mean()) if not final_sales_df.empty else 0.0
                    st.metric("Average Order Quantity", f"{avg_quantity:,.0f} kgs")

                st.write("")
                visuals_df = pd.DataFrame({
                    "Quantity Sold (kgs)": final_sales_df["Quantity"],
                    "Revenue (ugx)": final_sales_df["Total Price"],
                    "Date": final_sales_df["Date"],
                })

                # Row 1: Revenue trend
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    st.subheader("📈 Revenue Trend")
                    chart_height = 5 * 50
                    area = (
                        alt.Chart(visuals_df)
                        .mark_area(interpolate="monotone", opacity=0.2, color=chart_color)
                        .encode(
                            x=alt.X("month(Date):O", axis=alt.Axis(grid=False)),
                            y=alt.Y("sum(Revenue (ugx)):Q", axis=alt.Axis(grid=False)),
                        )
                    )
                    line = (
                        alt.Chart(visuals_df)
                        .mark_line(interpolate="monotone", color=chart_color, strokeWidth=2)
                        .encode(
                            x=alt.X("month(Date):O", axis=alt.Axis(grid=False)),
                            y=alt.Y("sum(Revenue (ugx)):Q", axis=alt.Axis(grid=False)),
                            tooltip=[
                                alt.Tooltip("month(Date):O", title="Month"),
                                alt.Tooltip("sum(Revenue (ugx)):Q", title="Total Revenue", format=","),
                            ],
                        )
                    )
                    points = line.mark_point(size=50, color=chart_color)
                    st.altair_chart((area + line + points).properties(height=chart_height), use_container_width=True)

                with row1_col2:
                    st.subheader("📊 Quantity Sold by Month")
                    bar_qty = (
                        alt.Chart(visuals_df)
                        .mark_bar(color=chart_color, size=20)
                        .encode(
                            x=alt.X("month(Date):O", scale=alt.Scale(paddingInner=0.4)),
                            y="sum(Quantity Sold (kgs)):Q",
                            tooltip=[
                                alt.Tooltip("month(Date):O", title="Month"),
                                alt.Tooltip("sum(Quantity Sold (kgs)):Q", title="Total Kgs", format=","),
                            ],
                        )
                    ).properties(height=chart_height)
                    st.altair_chart(bar_qty, use_container_width=True)

                st.write("")
                # Row 2: Top 5 + Table
                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    st.subheader("🏆 Top 5 Customers")
                    top5 = (
                        final_sales_df.groupby("Customer")["Total Price"]
                        .sum()
                        .nlargest(5)
                        .reset_index()
                    )
                    bar_top5 = (
                        alt.Chart(top5)
                        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusBottomLeft=3, size=20)
                        .encode(
                            x=alt.X("Total Price:Q", title="Sales"),
                            y=alt.Y("Customer:N", sort="-x", title="", scale=alt.Scale(paddingInner=0.4)),
                            tooltip=[
                                alt.Tooltip("Customer:N", title="Customer"),
                                alt.Tooltip("Total Price:Q", title="Total Sales", format=","),
                            ],
                        )
                        .properties(height=top5.shape[0] * 50)
                        .configure_mark(color=chart_color)
                    )
                    st.altair_chart(bar_top5, use_container_width=True)

                with row2_col2:
                    st.subheader("🗂️ Raw Data")
                    df_display = final_sales_df[["Date", "Customer", "Unit Price", "Quantity", "Total Price"]].copy()
                    df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
                    df_display = df_display.sort_values("Date", ascending=False).reset_index(drop=True)
                    df_display.index = df_display.index + 1
                    df_display.index.name = "No."
                    st.dataframe(df_display, use_container_width=True)

        with sales_form:
            st.title(":green[Sales]")
            with st.form(key="sales"):
                x1, x2 = st.columns(2)
                x3, x4 = st.columns(2)
                x5, x6 = st.columns(2)
                x7, x8 = st.columns(2)

                with x1:
                    date = st.date_input(
                        "Date (dd/mm/yyyy)",
                        value=datetime.datetime.now(),
                        format="DD/MM/YYYY",
                        max_value=datetime.datetime.now(),
                        min_value=datetime.date(2022, 8, 1),
                    )
                with x2:
                    customer = st.selectbox(
                        label="Customer", options=customers_list, placeholder="Select Customer", index=None
                    )
                with x3:
                    size = st.selectbox(label="Size", options=sfx.get_sizes())
                with x4:
                    unit = st.selectbox(label="Unit", options=sfx.get_units())
                with x5:
                    quantity = st.text_input(value=1, key="quantity", placeholder="0", label="Quantity")
                with x6:
                    unit_price = st.text_input(value=1, key="unit-price", placeholder="ugx", label="Unit Price")
                with x7:
                    total_price = st.number_input(label="Total Price", disabled=True, value=calculate_total_price())
                with x8:
                    amount_paid = st.text_input(key="amount_paid", placeholder="0", label="Amount Paid")

                delivery_fee = st.text_input(key="delivery", placeholder="0", label="Delivery Fee")

                sale_submitted = st.form_submit_button("Save", on_click=calculate_total_price)

                if sale_submitted:
                    tz_eat = tz("Africa/Nairobi")
                    timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")

                    data = [
                        timestamp,
                        date.strftime("%d/%m/%y"),
                        customer,
                        size,
                        unit,
                        unit_price,
                        quantity,
                        st.session_state["total-price"],
                        "payment_status is being dropped",
                        amount_paid,
                        delivery_fee,
                        current_user,
                    ]

                    with st.spinner("Saving sale data..."):
                        pepper_workbook = gc.open_by_url(st.secrets["sales_sheet_key"])
                        sales_sheet = pepper_workbook.worksheet("Final Sales")
                        next_row_index = len(sales_sheet.get_all_values()) + 1
                        sales_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )
                        st.success("✅ Sale saved Successfully")

    # ===================== DEPOSITS =====================
    elif nav_bar == "Deposits":
        deposits, deposit_form = st.tabs(["➕ Deposits", "📜 Form"])

        deposits_df = dfx.load_deposits()
        deposits_df = dfx.filter_data(deposits_df, "years", years)
        deposits_df = dfx.filter_data(deposits_df, "months", months)
        deposits_df = dfx.filter_data(deposits_df, "start_date", start_date)
        deposits_df = dfx.filter_data(deposits_df, "end_date", end_date)

        if current_user != "Victor Tindimwebwa":
            with deposits:
                if deposits_df.empty:
                    st.info("No records match the filtration criteria")
                unique_months_list = deposits_df["Date"].dt.month_name().unique().tolist()
                for month in unique_months_list:
                    month_df = dfx.process_deposit_month(deposits_df, month)
                    dfx.display_expander(month, month_df)

        with deposit_form:
            st.title(":green[Deposits]")
            with st.form(key="deposits", clear_on_submit=True):
                date = st.date_input(
                    "Date (dd/mm/yyyy)",
                    value=None,
                    format="DD/MM/YYYY",
                    max_value=datetime.datetime.now(),
                    min_value=datetime.date(2022, 8, 1),
                    help="Date **MUST** be before or equal to today",
                )
                amount = st.text_input(placeholder="ugx", label="Amount deposited", help="Enter a value > 0")

                st.info("Uploading an image of the deposit slip will come in the next release!")

                submitted = st.form_submit_button("Save")
                if submitted:
                    tz_eat = tz("Africa/Nairobi")
                    timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")

                    data = [
                        timestamp,
                        date.strftime("%d/%m/%y"),
                        int(str(amount).replace(",", "").strip() or "0"),
                        current_user,
                    ]

                    with st.spinner("Saving deposit data..."):
                        pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Deposits")
                        next_row_index = len(deposits_sheet.get_all_values()) + 1
                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )
                        st.success("✅ Deposit Saved Successfully. Feel free to close the application")

    # ===================== WITHDRAWS =====================
    elif nav_bar == "Withdraws":
        if current_user != "Victor Tindimwebwa":
            withdraws, withdraw_form = st.tabs(["➖ Withdraws", "📜 Form"])

            withdraw_df = wfx.load_withdraws()
            withdraw_df = wfx.filter_data(withdraw_df, "years", years)
            withdraw_df = wfx.filter_data(withdraw_df, "months", months)
            withdraw_df = wfx.filter_data(withdraw_df, "start_date", start_date)
            withdraw_df = wfx.filter_data(withdraw_df, "end_date", end_date)

            with withdraws:
                if withdraw_df.empty:
                    st.info("No records match the filtration criteria")
                unique_months_list = withdraw_df["Date"].dt.month_name().unique().tolist()
                for month in unique_months_list:
                    month_df = dfx.process_deposit_month(withdraw_df, month)
                    dfx.display_expander(month, month_df)

            with withdraw_form:
                st.title(":red[Withdraws]")
                with st.form(key="withdraws", clear_on_submit=True):
                    date = st.date_input(
                        "Date (dd/mm/yyyy)",
                        value=None,
                        format="DD/MM/YYYY",
                        max_value=datetime.datetime.now(),
                        min_value=datetime.date(2022, 8, 1),
                        help="Date **MUST** be before or equal to today",
                    )
                    amount = st.text_input(placeholder="ugx", label="Amount withdrawn", help="Enter a value > 0")
                    reason_for_withdraw = st.text_input(placeholder="reason for withdraw", label="Reason for Withdraw")

                    submitted = st.form_submit_button("Save")
                    if submitted:
                        tz_eat = tz("Africa/Nairobi")
                        timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")

                        data = [
                            timestamp,
                            date.strftime("%d/%b/%Y"),
                            int(str(amount).replace(",", "").strip() or "0"),
                            reason_for_withdraw,
                            current_user,
                        ]

                        with st.spinner("Saving withdraw data..."):
                            pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                            withdraws_sheet = pepper_workbook.worksheet("Withdraws")
                            next_row_index = len(withdraws_sheet.get_all_values()) + 1
                            withdraws_sheet.append_rows(
                                [data],
                                value_input_option="user_entered",
                                insert_data_option="insert_rows",
                                table_range=f"a{next_row_index}",
                            )
                            st.success("✅ Withdraw Saved Successfully. Feel free to close the application")

    # ===================== HARVESTS =====================
    elif nav_bar == "Harvests":
        harvests_df = hfx.get_harvests_df()
        st.dataframe(harvests_df, use_container_width=True)

    # ---- Logout ----
    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
