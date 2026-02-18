import datetime

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import set_with_dataframe
from millify import millify
from pytz import timezone as tz
from streamlit_option_menu import option_menu

import cost_functions as cfx
import customers_functions as cusfx
import deposit_functions as dfx
import general_functions as gfx
import harvest_functions as hfx
import sales_functions as sfx
import withdraw_functions as wfx

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
        options = ["Costs", "Sales", "Harvests", "Customers", "Deposits", "Withdraws"]
        icons = [
            "bar-chart-line",
            "coin",
            "flower3",
            "people",
            "node-plus",
            "node-minus",
        ]

        # pick default index from session_state (safe fallback to 0)
        default_index = (
            options.index(st.session_state["nav_bar_selection"])
            if st.session_state.get("nav_bar_selection") in options
            else 0
        )

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
            years, months, cost_categories, customers, start_date, end_date = (
                gfx.show_filters(nav_bar_selection=st.session_state["nav_bar"])
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
        details, dashboard, costs_form = st.tabs(
            ["📝 Details", "💰 Dashboard", "📜 Form"]
        )

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

        if current_user != "Victor Tindimwebwa":
            with dashboard:
                if expenses_df.empty:
                    st.info("No cost data available for the selected filters")
                else:
                    # Prepare data for visualizations
                    visuals_df = pd.DataFrame(
                        {
                            "Category": expenses_df["Cost Category"],
                            "Cost": expenses_df["Total Cost"],
                            "Date": expenses_df["Date"],
                        }
                    )

                    # Add custom CSS to reduce metric font sizes
                    st.markdown(
                        """
                    <style>
                    div[data-testid="metric-container"] > div[data-testid="metric"] > div > div {
                        font-size: 1.2rem !important;
                    }
                    </style>
                    """,
                        unsafe_allow_html=True,
                    )

                    # Primary KPIs - Row 1
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_costs = float(visuals_df["Cost"].sum()) if not visuals_df.empty else 0.0
                        st.metric("💸 Total Costs", f"{total_costs:,.0f} UGX")

                    with col2:
                        total_transactions = len(visuals_df)
                        st.metric("🧾 Total Transactions", f"{total_transactions:,}")

                    with col3:
                        unique_categories = visuals_df["Category"].nunique()
                        st.metric("📂 Active Categories", f"{unique_categories}")

                    with col4:
                        number_of_months = visuals_df["Date"].dt.month.nunique() if not visuals_df.empty else 0
                        st.metric("📅 Months Covered", f"{number_of_months}")

                    # Secondary KPIs - Row 2
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        average_monthly_cost = total_costs / number_of_months if number_of_months > 0 else 0
                        st.metric("📊 Avg Monthly Cost", f"{average_monthly_cost:,.0f} UGX")

                    with col6:
                        avg_cost_per_transaction = total_costs / total_transactions if total_transactions > 0 else 0
                        st.metric("💳 Avg per Transaction", f"{avg_cost_per_transaction:,.0f} UGX")

                    with col7:
                        number_of_weeks = (visuals_df["Date"].max() - visuals_df["Date"].min()).days // 7 if not visuals_df.empty else 0
                        avg_weekly_cost = total_costs / number_of_weeks if number_of_weeks > 0 else 0
                        st.metric("📈 Avg Weekly Cost", f"{avg_weekly_cost:,.0f} UGX")

                    with col8:
                        # Top category by cost
                        top_category = visuals_df.groupby("Category")["Cost"].sum().idxmax() if not visuals_df.empty else "N/A"
                        st.metric("🏆 Top Category", top_category)

                    # Performance Insights Section
                    st.divider()
                    st.subheader("🎯 Cost Insights")

                    insight_col1, insight_col2 = st.columns(2)

                    with insight_col1:
                        # Highest cost month
                        monthly_costs = visuals_df.groupby(
                            visuals_df["Date"].dt.strftime("%B %Y")
                        )["Cost"].sum()
                        highest_month = monthly_costs.idxmax() if not monthly_costs.empty else "N/A"
                        highest_month_value = monthly_costs.max() if not monthly_costs.empty else 0

                        st.warning(
                            f"""
                        **📈 Highest Cost Month**  
                        {highest_month}  
                        Cost: {highest_month_value:,.0f} UGX
                        """
                        )

                    with insight_col2:
                        # Lowest cost month
                        lowest_month = monthly_costs.idxmin() if not monthly_costs.empty else "N/A"
                        lowest_month_value = monthly_costs.min() if not monthly_costs.empty else 0

                        st.success(
                            f"""
                        **📉 Lowest Cost Month**  
                        {lowest_month}  
                        Cost: {lowest_month_value:,.0f} UGX
                        """
                        )

                    st.divider()

                    # Chart colors
                    chart_color = "#DC143C"  # Crimson red for costs
                    chart_color_dark = "#8B0000"  # Dark red
                    chart_color_light = "#FFB6C1"  # Light pink

                    # Analytics Section
                    st.subheader("📊 Cost Analytics")

                    # Row 1: Time-based Analysis
                    row1_col1, row1_col2 = st.columns(2)

                    with row1_col1:
                        st.markdown("**📅 Costs by Month**")
                        monthly_costs_df = (
                            visuals_df.groupby(visuals_df["Date"].dt.to_period("M"))["Cost"]
                            .sum()
                            .reset_index()
                        )
                        monthly_costs_df["Date"] = monthly_costs_df["Date"].astype(str)

                        area_chart = (
                            alt.Chart(monthly_costs_df)
                            .mark_area(
                                interpolate="monotone",
                                opacity=0.3,
                                color=chart_color,
                                line={"color": chart_color_dark, "strokeWidth": 3},
                            )
                            .encode(
                                x=alt.X(
                                    "Date:O",
                                    title="Month",
                                    axis=alt.Axis(grid=False, labelAngle=-45),
                                ),
                                y=alt.Y(
                                    "Cost:Q",
                                    title="Cost (UGX)",
                                    axis=alt.Axis(grid=False, format=".2s"),
                                ),
                                tooltip=[
                                    alt.Tooltip("Date:O", title="Month"),
                                    alt.Tooltip("Cost:Q", title="Cost", format=",.0f"),
                                ],
                            )
                            .properties(height=300)
                        )

                        st.altair_chart(area_chart, use_container_width=True)

                    with row1_col2:
                        st.markdown("**📊 Daily Cost Trend (Last 30 Days)**")
                        daily_costs = (
                            visuals_df.groupby(visuals_df["Date"].dt.date)["Cost"]
                            .sum()
                            .reset_index()
                        )
                        daily_costs = daily_costs.tail(30)  # Last 30 days

                        daily_chart = (
                            alt.Chart(daily_costs)
                            .mark_bar(
                                color=chart_color,
                                cornerRadiusTopLeft=3,
                                cornerRadiusTopRight=3,
                            )
                            .encode(
                                x=alt.X(
                                    "Date:T",
                                    title="Date",
                                    axis=alt.Axis(grid=False, format="%d/%m"),
                                ),
                                y=alt.Y(
                                    "Cost:Q",
                                    title="Daily Cost",
                                    axis=alt.Axis(grid=False, format=".2s"),
                                ),
                                tooltip=[
                                    alt.Tooltip("Date:T", title="Date", format="%d/%b/%Y"),
                                    alt.Tooltip("Cost:Q", title="Cost", format=",.0f"),
                                ],
                            )
                            .properties(height=300)
                        )

                        st.altair_chart(daily_chart, use_container_width=True)

                    # Row 2: Category Analysis
                    row2_col1, row2_col2 = st.columns(2)

                    with row2_col1:
                        st.markdown("**🏆 Top Categories by Cost**")
                        top_categories = (
                            visuals_df.groupby("Category")["Cost"]
                            .sum()
                            .nlargest(10)
                            .reset_index()
                        )

                        category_chart = (
                            alt.Chart(top_categories)
                            .mark_bar(
                                color=chart_color,
                                cornerRadiusTopLeft=5,
                                cornerRadiusBottomLeft=5,
                            )
                            .encode(
                                x=alt.X(
                                    "Cost:Q",
                                    title="Total Cost (UGX)",
                                    axis=alt.Axis(format=".2s"),
                                ),
                                y=alt.Y(
                                    "Category:N",
                                    sort="-x",
                                    title="",
                                    axis=alt.Axis(labelLimit=150),
                                ),
                                tooltip=[
                                    alt.Tooltip("Category:N", title="Category"),
                                    alt.Tooltip("Cost:Q", title="Total Cost", format=",.0f"),
                                ],
                            )
                            .properties(height=400)
                        )

                        st.altair_chart(category_chart, use_container_width=True)

                    with row2_col2:
                        st.markdown("**📋 Category Performance Summary**")
                        # Create a summary table of category metrics
                        category_metrics = (
                            visuals_df.groupby("Category")
                            .agg({"Cost": ["sum", "count", "mean"]})
                            .round(0)
                        )

                        # Flatten column names
                        category_metrics.columns = [
                            "Total Cost",
                            "Transactions",
                            "Avg per Transaction",
                        ]
                        category_metrics = category_metrics.sort_values(
                            "Total Cost", ascending=False
                        ).head(10)

                        # Format for display
                        category_metrics["Total Cost"] = category_metrics["Total Cost"].apply(
                            lambda x: f"{x:,.0f}"
                        )
                        category_metrics["Avg per Transaction"] = category_metrics[
                            "Avg per Transaction"
                        ].apply(lambda x: f"{x:,.0f}")

                        st.dataframe(category_metrics, use_container_width=True, height=350)

                    # Row 3: Cost Distribution
                    st.divider()
                    st.markdown("**🥧 Cost Distribution by Category**")
                    
                    pie_col1, pie_col2 = st.columns([2, 1])
                    
                    with pie_col1:
                        pie = (
                            alt.Chart(visuals_df)
                            .mark_arc(innerRadius=80)
                            .encode(
                                theta=alt.Theta("sum(Cost):Q", title="Cost"),
                                color=alt.Color(
                                    "Category:N",
                                    legend=alt.Legend(orient="right", titleFontSize=12, labelLimit=150)
                                ),
                                tooltip=[
                                    alt.Tooltip("Category:N", title="Category"),
                                    alt.Tooltip("sum(Cost):Q", title="Total Cost", format=",.0f"),
                                ],
                            )
                            .properties(height=350)
                        )
                        st.altair_chart(pie, use_container_width=True)
                    
                    with pie_col2:
                        # Cost breakdown percentages
                        st.markdown("**📊 Top 5 by %**")
                        category_totals = visuals_df.groupby("Category")["Cost"].sum().sort_values(ascending=False)
                        top_5_pct = category_totals.head(5)
                        total_cost_sum = category_totals.sum()
                        
                        for cat, cost in top_5_pct.items():
                            pct = (cost / total_cost_sum * 100) if total_cost_sum > 0 else 0
                            st.metric(
                                label=cat[:20] + "..." if len(cat) > 20 else cat,
                                value=f"{pct:.1f}%",
                                delta=f"{cost:,.0f} UGX"
                            )

        with costs_form:
            st.title(":red[Costs]")

            with st.form(key="costs"):
                c1, c2 = st.columns(2)
                c3, c6 = st.columns(2)
                # c5, c6 = st.columns(2)
                # c7, c8 = st.columns(2)

                with c1:
                    date = st.date_input(
                        "Date (dd/mm/yyyy)",
                        value=datetime.datetime.now(),
                        format="DD/MM/YYYY",
                        max_value=datetime.datetime.now(),
                        min_value=datetime.date(2022, 8, 1),
                    )
                with c2:
                    category = st.selectbox(
                        label="Category", index=None, options=cfx.get_cost_categories()
                    )
                with c3:
                    narrative = st.text_input(label="Narrative *", help="Required: Brief description of the cost")
                # with c4:
                #     cost_quantity = st.text_input(label="Quantity")
                # with c5:
                #     unit_cost = st.text_input(
                #         key="unit-cost", placeholder="ugx", label="Unit Cost"
                #     )
                with c6:
                    total_cost = st.text_input(placeholder="ugx", label="Total Cost")
                # with c7:
                #     transport_cost = st.text_input(
                #         placeholder="ugx", label="Transport Cost (if any)"
                #     )
                # with c8:
                #     transport_details = st.text_input(
                #         placeholder="eg: from seeta to farm",
                #         label="Transport Details (if any)",
                #     )

                source_of_funds = st.selectbox(
                    "Source of Money",
                    (
                        ["Bank", "Personal", "Sales"]
                        if current_user in {"Andrew", "Tony"}
                        else ["Bank", "Sales"]
                    ),
                )

                cost_submitted = st.form_submit_button("Save")

                if cost_submitted:
                    # Validate narrative is not empty
                    if not narrative or narrative.strip() == "":
                        st.error("❌ Narrative is required. Please provide a description of the cost.")
                    elif not category:
                        st.error("❌ Please select a category.")
                    elif not total_cost or total_cost.strip() == "":
                        st.error("❌ Total Cost is required.")
                    else:
                        tz_eat = tz("Africa/Nairobi")
                        timestamp = datetime.datetime.now(tz_eat).strftime(
                            "%d-%b-%Y %H:%M:%S EAT"
                        )

                        data = [
                            timestamp,
                            date.strftime("%d/%m/%y"),
                            narrative,
                            category,
                            "",
                            "",  # cost_quantity (commented out)
                            "",
                            "",  # unit_cost (commented out)
                            total_cost,
                            "",  # transport_cost (commented out)
                            "",  # transport_details (commented out)
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
        sales_details, sales_dashboard, sales_form = st.tabs(
            ["📝 Details", "💰 Dashboard", "📜 Form"]
        )

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
                else:
                    # Create a comprehensive sales overview
                    st.subheader("📊 Sales Overview")

                    # Summary metrics in columns
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_sales = len(final_sales_df)
                        st.metric("Total Transactions", f"{total_sales:,}")
                    with col2:
                        total_revenue = pd.to_numeric(
                            final_sales_df["Total Price"], errors="coerce"
                        ).sum()
                        st.metric("Total Revenue", f"{total_revenue:,.0f} UGX")
                    with col3:
                        total_quantity = pd.to_numeric(
                            final_sales_df["Quantity"], errors="coerce"
                        ).sum()
                        st.metric("Total Quantity", f"{total_quantity:,.1f} kg")
                    with col4:
                        unique_customers = final_sales_df["Customer"].nunique()
                        st.metric("Unique Customers", f"{unique_customers}")

                    st.divider()

                    # Prepare the sales data for display
                    display_df = final_sales_df.copy()

                    # Sort by date (newest first)
                    display_df = display_df.sort_values("Date", ascending=False)

                    # Format the Date column for display
                    display_df["Date"] = display_df["Date"].apply(
                        lambda x: x.strftime("%d/%b/%Y") if pd.notnull(x) else ""
                    )

                    # Format numeric columns
                    display_df["Unit Price"] = pd.to_numeric(
                        display_df["Unit Price"], errors="coerce"
                    ).apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "0")
                    display_df["Total Price"] = pd.to_numeric(
                        display_df["Total Price"], errors="coerce"
                    ).apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "0")
                    display_df["Quantity"] = pd.to_numeric(
                        display_df["Quantity"], errors="coerce"
                    ).apply(lambda x: f"{x:,.1f}" if pd.notnull(x) else "0")

                    # Reset index and create a transaction number
                    display_df = display_df.reset_index(drop=True)
                    display_df.index += 1

                    # Reorder columns for better presentation
                    column_order = [
                        "Date",
                        "Customer",
                        "Size",
                        "Quantity",
                        "Unit",
                        "Unit Price",
                        "Total Price",
                    ]
                    display_df = display_df[column_order]

                    st.subheader("🔄 All Sales Transactions (Latest First)")

                    # Display the table with better formatting
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        column_config={
                            "Date": st.column_config.TextColumn(
                                "📅 Date", width="small"
                            ),
                            "Customer": st.column_config.TextColumn(
                                "👤 Customer", width="medium"
                            ),
                            "Size": st.column_config.TextColumn(
                                "📏 Size", width="small"
                            ),
                            "Quantity": st.column_config.TextColumn(
                                "⚖️ Quantity", width="small"
                            ),
                            "Unit": st.column_config.TextColumn(
                                "📦 Unit", width="small"
                            ),
                            "Unit Price": st.column_config.TextColumn(
                                "💰 Unit Price (UGX)", width="small"
                            ),
                            "Total Price": st.column_config.TextColumn(
                                "💵 Total (UGX)", width="small"
                            ),
                        },
                        height=600,
                    )

        chart_color = "#D4A017"
        chart_color_light = "#F4E4B8"  # Lighter version for better elegance
        chart_color_dark = "#B8860B"  # Darker version for contrast

        if current_user != "Victor Tindimwebwa":
            with sales_dashboard:
                if final_sales_df.empty:
                    st.info("No sales data available for the selected filters")
                else:
                    # Enhanced KPIs Section

                    # Add custom CSS to reduce metric font sizes
                    st.markdown(
                        """
                    <style>
                    div[data-testid="metric-container"] > div[data-testid="metric"] > div > div {
                        font-size: 1.2rem !important;
                    }
                    </style>
                    """,
                        unsafe_allow_html=True,
                    )

                    # Primary KPIs - Row 1
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_revenue = pd.to_numeric(
                            final_sales_df["Total Price"], errors="coerce"
                        ).sum()
                        st.metric("💰 Total Revenue", f"{total_revenue:,.0f} UGX")

                    with col2:
                        total_transactions = len(final_sales_df)
                        st.metric("🧾 Total Transactions", f"{total_transactions:,}")

                    with col3:
                        total_quantity = pd.to_numeric(
                            final_sales_df["Quantity"], errors="coerce"
                        ).sum()
                        st.metric("⚖️ Total Quantity", f"{total_quantity:,.1f} kg")

                    with col4:
                        unique_customers = final_sales_df["Customer"].nunique()
                        st.metric("👥 Active Customers", f"{unique_customers}")

                    # Secondary KPIs - Row 2
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        avg_order_value = (
                            total_revenue / total_transactions
                            if total_transactions > 0
                            else 0
                        )
                        st.metric("📊 Avg Order Value", f"{avg_order_value:,.0f} UGX")

                    with col6:
                        avg_unit_price = pd.to_numeric(
                            final_sales_df["Unit Price"], errors="coerce"
                        ).mean()
                        st.metric("🏷️ Avg Unit Price", f"{avg_unit_price:,.0f} UGX/kg")

                    with col7:
                        avg_quantity_per_order = (
                            total_quantity / total_transactions
                            if total_transactions > 0
                            else 0
                        )
                        st.metric(
                            "📦 Avg Order Size", f"{avg_quantity_per_order:.1f} kg"
                        )

                    with col8:
                        avg_customer_value = (
                            total_revenue / unique_customers
                            if unique_customers > 0
                            else 0
                        )
                        st.metric(
                            "💎 Avg Customer Value", f"{avg_customer_value:,.0f} UGX"
                        )

                    # Performance Insights Section - Moved right after KPIs
                    st.divider()
                    st.subheader("🎯 Performance Insights")

                    # Prepare data for insights calculations
                    visuals_df = final_sales_df.copy()
                    visuals_df["Revenue"] = pd.to_numeric(
                        visuals_df["Total Price"], errors="coerce"
                    )
                    visuals_df["Quantity"] = pd.to_numeric(
                        visuals_df["Quantity"], errors="coerce"
                    )
                    visuals_df["Date"] = pd.to_datetime(visuals_df["Date"])

                    insight_col1, insight_col2 = st.columns(2)

                    with insight_col1:
                        # Best performing month
                        monthly_perf = visuals_df.groupby(
                            visuals_df["Date"].dt.strftime("%B %Y")
                        )["Revenue"].sum()
                        best_month = (
                            monthly_perf.idxmax() if not monthly_perf.empty else "N/A"
                        )
                        best_month_value = (
                            monthly_perf.max() if not monthly_perf.empty else 0
                        )

                        st.info(
                            f"""
                        **🏆 Best Month**  
                        {best_month}  
                        Revenue: {best_month_value:,.0f} UGX
                        """
                        )

                    with insight_col2:
                        # Worst performing month
                        worst_month = (
                            monthly_perf.idxmin() if not monthly_perf.empty else "N/A"
                        )
                        worst_month_value = (
                            monthly_perf.min() if not monthly_perf.empty else 0
                        )

                        st.warning(
                            f"""
                        **📉 Worst Month**  
                        {worst_month}  
                        Revenue: {worst_month_value:,.0f} UGX
                        """
                        )

                    st.divider()

                    # Prepare data for visualizations

                    # Analytics Section
                    st.subheader("📈 Sales Analytics")

                    # Row 1: Time-based Analysis
                    row1_col1, row1_col2 = st.columns(2)

                    with row1_col1:
                        st.markdown("**📅 Revenue by Month**")
                        monthly_revenue = (
                            visuals_df.groupby(visuals_df["Date"].dt.to_period("M"))[
                                "Revenue"
                            ]
                            .sum()
                            .reset_index()
                        )
                        monthly_revenue["Date"] = monthly_revenue["Date"].astype(str)

                        area_chart = (
                            alt.Chart(monthly_revenue)
                            .mark_area(
                                interpolate="monotone",
                                opacity=0.3,
                                color=chart_color,
                                line={"color": chart_color_dark, "strokeWidth": 3},
                            )
                            .encode(
                                x=alt.X(
                                    "Date:O",
                                    title="Month",
                                    axis=alt.Axis(grid=False, labelAngle=-45),
                                ),
                                y=alt.Y(
                                    "Revenue:Q",
                                    title="Revenue (UGX)",
                                    axis=alt.Axis(grid=False, format=".2s"),
                                ),
                                tooltip=[
                                    alt.Tooltip("Date:O", title="Month"),
                                    alt.Tooltip(
                                        "Revenue:Q", title="Revenue", format=",.0f"
                                    ),
                                ],
                            )
                            .properties(height=300)
                        )

                        st.altair_chart(area_chart, use_container_width=True)

                    with row1_col2:
                        st.markdown("**📊 Daily Sales Performance**")
                        daily_sales = (
                            visuals_df.groupby(visuals_df["Date"].dt.date)
                            .agg({"Revenue": "sum", "Quantity": "sum"})
                            .reset_index()
                        )
                        daily_sales = daily_sales.tail(30)  # Last 30 days

                        daily_chart = (
                            alt.Chart(daily_sales)
                            .mark_bar(
                                color=chart_color,
                                cornerRadiusTopLeft=3,
                                cornerRadiusTopRight=3,
                            )
                            .encode(
                                x=alt.X(
                                    "Date:T",
                                    title="Date",
                                    axis=alt.Axis(grid=False, format="%d/%m"),
                                ),
                                y=alt.Y(
                                    "Revenue:Q",
                                    title="Daily Revenue",
                                    axis=alt.Axis(grid=False, format=".2s"),
                                ),
                                tooltip=[
                                    alt.Tooltip(
                                        "Date:T", title="Date", format="%d/%b/%Y"
                                    ),
                                    alt.Tooltip(
                                        "Revenue:Q", title="Revenue", format=",.0f"
                                    ),
                                    alt.Tooltip(
                                        "Quantity:Q", title="Quantity", format=",.1f"
                                    ),
                                ],
                            )
                            .properties(height=300)
                        )

                        st.altair_chart(daily_chart, use_container_width=True)

                    # Row 2: Customer and Product Analysis
                    row2_col1, row2_col2 = st.columns(2)

                    with row2_col1:
                        st.markdown("**🏆 Top 10 Customers by Revenue**")
                        top_customers = (
                            visuals_df.groupby("Customer")["Revenue"]
                            .sum()
                            .nlargest(10)
                            .reset_index()
                        )

                        customer_chart = (
                            alt.Chart(top_customers)
                            .mark_bar(
                                color=chart_color,
                                cornerRadiusTopLeft=5,
                                cornerRadiusBottomLeft=5,
                            )
                            .encode(
                                x=alt.X(
                                    "Revenue:Q",
                                    title="Revenue (UGX)",
                                    axis=alt.Axis(format=".2s"),
                                ),
                                y=alt.Y(
                                    "Customer:N",
                                    sort="-x",
                                    title="",
                                    axis=alt.Axis(labelLimit=100),
                                ),
                                tooltip=[
                                    alt.Tooltip("Customer:N", title="Customer"),
                                    alt.Tooltip(
                                        "Revenue:Q",
                                        title="Total Revenue",
                                        format=",.0f",
                                    ),
                                ],
                            )
                            .properties(height=400)
                        )

                        st.altair_chart(customer_chart, use_container_width=True)

                    with row2_col2:
                        st.markdown("**🏆 Customer Performance Summary**")
                        # Create a summary table of customer metrics
                        customer_metrics = (
                            visuals_df.groupby("Customer")
                            .agg(
                                {"Revenue": ["sum", "count", "mean"], "Quantity": "sum"}
                            )
                            .round(1)
                        )

                        # Flatten column names
                        customer_metrics.columns = [
                            "Total Revenue",
                            "Transactions",
                            "Avg Order Value",
                            "Total Quantity",
                        ]
                        customer_metrics = customer_metrics.sort_values(
                            "Total Revenue", ascending=False
                        ).head(8)

                        # Format for display
                        customer_metrics["Total Revenue"] = customer_metrics[
                            "Total Revenue"
                        ].apply(lambda x: f"{x:,.0f}")
                        customer_metrics["Avg Order Value"] = customer_metrics[
                            "Avg Order Value"
                        ].apply(lambda x: f"{x:,.0f}")
                        customer_metrics["Total Quantity"] = customer_metrics[
                            "Total Quantity"
                        ].apply(lambda x: f"{x:.1f}")

                        st.dataframe(
                            customer_metrics, use_container_width=True, height=350
                        )

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
                        label="Customer",
                        options=customers_list,
                        placeholder="Select Customer",
                        index=None,
                    )
                with x3:
                    size = st.selectbox(label="Size", options=sfx.get_sizes())
                with x4:
                    unit = st.selectbox(label="Unit", options=sfx.get_units())
                with x5:
                    quantity = st.number_input(
                        label="Quantity",
                        min_value=0.0,
                        value=1.0,
                        step=0.1,
                        key="quantity_input"
                    )
                with x6:
                    unit_price = st.number_input(
                        label="Unit Price",
                        min_value=0.0,
                        value=0.0,
                        step=100.0,
                        key="unit_price_input"
                    )
                with x7:
                    st.markdown("<div style='padding-top: 28px;'><small style='color: #888888;'>💡 Total price will be computed automatically based on quantity × unit price</small></div>", unsafe_allow_html=True)
                with x8:
                    amount_paid = st.number_input(
                        label="Amount Paid by Customer",
                        min_value=0.0,
                        value=0.0,
                        step=100.0,
                        key="amount_paid_input"
                    )

                submitted = st.form_submit_button("Submit")
                if submitted:
                    if customer and size and unit and quantity > 0 and unit_price > 0:
                        # Create timestamp in the required format
                        tz_eat = tz("Africa/Nairobi")
                        timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")
                        
                        # Format date as dd/mm/yy
                        formatted_date = date.strftime("%d/%m/%y")
                        
                        # Calculate total price
                        calculated_total = quantity * unit_price
                        
                        # Prepare the data in the exact order required by the sheet
                        # timestamp, date, customer, size, unit, unit price, quantity, total price, Payment Status, amount paid, transportation cost, entered by
                        sale_data = {
                            "timestamp": timestamp,
                            "date": formatted_date,
                            "customer": customer,
                            "size": size,
                            "unit": unit,
                            "unit price": unit_price,
                            "quantity": quantity,
                            "total price": calculated_total,
                            "Payment Status": "",  # Empty as requested
                            "amount paid": amount_paid,
                            "transportation cost": "",  # Empty as requested
                            "entered by": current_user,
                        }

                        # Write to Google Sheets
                        pepper_workbook = gc.open_by_url(st.secrets["sales_sheet_key"])
                        sales_sheet = pepper_workbook.worksheet("Final Sales")
                        next_row_index = len(sales_sheet.get_all_values()) + 1
                        set_with_dataframe(
                            sales_sheet,
                            pd.DataFrame([sale_data]),
                            row=next_row_index,
                            include_column_header=False,
                            include_index=False,
                        )
                        st.success("✅ Sale saved Successfully")

    # ===================== CUSTOMERS =====================
    elif nav_bar == "Customers":
        st.title("👥 Customer Management")
        
        # Create tabs for different customer operations
        tab1, tab2, tab3 = st.tabs(["📊 Customer Analytics", "📋 Customer Directory", "➕ Add New Customer"])
        
        with tab1:
            # Get sales data for customer analysis
            final_sales_df = sfx.get_sales_df()
            final_sales_df = sfx.filter_data(final_sales_df, "years", years)
            final_sales_df = sfx.filter_data(final_sales_df, "months", months)
            final_sales_df = sfx.filter_data(final_sales_df, "customers", customers)
            final_sales_df = sfx.filter_data(final_sales_df, "start_date", start_date)
            final_sales_df = sfx.filter_data(final_sales_df, "end_date", end_date)

            if final_sales_df.empty:
                st.info("No customer data available for the selected filters")
            else:
                # Customer Overview Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_customers = final_sales_df["Customer"].nunique()
                    st.metric("Total Customers", f"{total_customers}")
                with col2:
                    avg_customer_value = (
                        pd.to_numeric(final_sales_df["Total Price"], errors="coerce")
                        .groupby(final_sales_df["Customer"])
                        .sum()
                        .mean()
                    )
                    st.metric("Avg Customer Value", f"{avg_customer_value:,.0f} UGX")
                with col3:
                    customer_totals = (
                        pd.to_numeric(final_sales_df["Total Price"], errors="coerce")
                        .groupby(final_sales_df["Customer"])
                        .sum()
                    )
                    top_customer_value = customer_totals.max()
                    top_customer_name = customer_totals.idxmax()
                    st.metric(
                        "Top Customer Value",
                        f"{top_customer_value:,.0f} UGX",
                        delta=f"{top_customer_name}",
                    )
                with col4:
                    avg_transactions = final_sales_df.groupby("Customer").size().mean()
                    st.metric("Avg Transactions/Customer", f"{avg_transactions:.1f}")

                st.divider()

                # Customer Summary Table
                st.subheader("👥 Customer Summary & Analytics")

                # Group by customer and create comprehensive summary
                customer_summary = (
                    final_sales_df.groupby("Customer")
                    .agg(
                        {
                            "Quantity": lambda x: pd.to_numeric(x, errors="coerce").sum(),
                            "Total Price": lambda x: pd.to_numeric(
                                x, errors="coerce"
                            ).sum(),
                            "Date": [
                                "count",
                                "min",
                                "max",
                            ],  # Number of transactions, first purchase, last purchase
                        }
                    )
                    .round(1)
                )

                # Flatten column names
                customer_summary.columns = [
                    "Total Quantity (kg)",
                    "Total Revenue (UGX)",
                    "Transactions",
                    "First Purchase",
                    "Last Purchase",
                ]

                # Format the data
                customer_summary = customer_summary.sort_values(
                    "Total Revenue (UGX)", ascending=False
                )
                customer_summary["Total Revenue (UGX)"] = customer_summary[
                    "Total Revenue (UGX)"
                ].apply(lambda x: f"{x:,.0f}")
                customer_summary["Total Quantity (kg)"] = customer_summary[
                    "Total Quantity (kg)"
                ].apply(lambda x: f"{x:,.1f}")

                # Format dates
                customer_summary["First Purchase"] = pd.to_datetime(
                    customer_summary["First Purchase"]
                ).dt.strftime("%d/%b/%Y")
                customer_summary["Last Purchase"] = pd.to_datetime(
                    customer_summary["Last Purchase"]
                ).dt.strftime("%d/%b/%Y")

                # Calculate average order value
                temp_df = final_sales_df.groupby("Customer").agg(
                    {
                        "Total Price": lambda x: pd.to_numeric(x, errors="coerce").sum(),
                        "Date": "count",
                    }
                )
                avg_order_value = (temp_df["Total Price"] / temp_df["Date"]).round(0)
                customer_summary["Avg Order Value (UGX)"] = avg_order_value.apply(
                    lambda x: f"{x:,.0f}"
                )

                # Reorder columns for better presentation
                column_order = [
                    "Total Revenue (UGX)",
                    "Transactions",
                    "Avg Order Value (UGX)",
                    "Total Quantity (kg)",
                    "First Purchase",
                    "Last Purchase",
                ]
                customer_summary = customer_summary[column_order]

                st.dataframe(
                    customer_summary,
                    use_container_width=True,
                    column_config={
                        "Total Revenue (UGX)": st.column_config.TextColumn(
                            "💰 Total Revenue", width="medium"
                        ),
                        "Transactions": st.column_config.NumberColumn(
                            "🔢 Transactions", width="small"
                        ),
                        "Avg Order Value (UGX)": st.column_config.TextColumn(
                            "📊 Avg Order Value", width="medium"
                        ),
                        "Total Quantity (kg)": st.column_config.TextColumn(
                            "⚖️ Total Quantity", width="medium"
                        ),
                        "First Purchase": st.column_config.TextColumn(
                            "🗓️ First Purchase", width="medium"
                        ),
                        "Last Purchase": st.column_config.TextColumn(
                            "📅 Last Purchase", width="medium"
                        ),
                    },
                    height=500,
                )

                st.info(
                    "💡 **Future Features**: Customer contact management, loyalty programs, and detailed purchase history will be added here."
                )
        
        with tab2:
            # Display customers table
            cusfx.display_customers_table()
        
        with tab3:
            # Customer creation form
            cusfx.create_customer_form()

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
                # Sort months chronologically from newest to oldest
                deposits_df_sorted = deposits_df.sort_values("Date", ascending=False)
                unique_months_list = (
                    deposits_df_sorted["Date"].dt.month_name().unique().tolist()
                )
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
                amount = st.text_input(
                    placeholder="ugx",
                    label="Amount deposited",
                    help="Enter a value > 0",
                )

                st.info(
                    "Uploading an image of the deposit slip will come in the next release!"
                )

                submitted = st.form_submit_button("Save")
                if submitted:
                    tz_eat = tz("Africa/Nairobi")
                    timestamp = datetime.datetime.now(tz_eat).strftime(
                        "%d-%b-%Y %H:%M:%S EAT"
                    )

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
                        st.success(
                            "✅ Deposit Saved Successfully. Feel free to close the application"
                        )

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
                    st.info("No records match the filteration criteria")
                # Sort months chronologically from newest to oldest
                withdraw_df_sorted = withdraw_df.sort_values("Date", ascending=False)
                unique_months_list = (
                    withdraw_df_sorted["Date"].dt.month_name().unique().tolist()
                )
                for month in unique_months_list:
                    month_df = wfx.process_withdraw_month(withdraw_df, month)
                    wfx.display_expander(month, month_df)

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
                    amount = st.text_input(
                        placeholder="ugx",
                        label="Amount withdrawn",
                        help="Enter a value > 0",
                    )
                    reason_for_withdraw = st.text_input(
                        placeholder="reason for withdraw", label="Reason for Withdraw"
                    )

                    submitted = st.form_submit_button("Save")
                    if submitted:
                        tz_eat = tz("Africa/Nairobi")
                        timestamp = datetime.datetime.now(tz_eat).strftime(
                            "%d-%b-%Y %H:%M:%S EAT"
                        )

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
                            st.success(
                                "✅ Withdraw Saved Successfully. Feel free to close the application"
                            )

    # ===================== HARVESTS =====================
    elif nav_bar == "Harvests":
        st.title("🌱 Harvest Management")
        
        # Load customers for the form
        customers_list = cusfx.load_customers()
        
        # Create tabs for different harvest operations
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📋 Harvest List", "➕ Add Harvest"])
        
        with tab1:
            # Load combined data for overview
            harvests_df = hfx.load_all_harvests_data()
            detailed_df = hfx.load_new_harvests_data()
            
            # Apply filters to both datasets
            if not harvests_df.empty:
                harvests_df = hfx.filter_data(harvests_df, "years", years)
                harvests_df = hfx.filter_data(harvests_df, "months", months)
                harvests_df = hfx.filter_data(harvests_df, "customers", customers)
                harvests_df = hfx.filter_data(harvests_df, "start_date", start_date)
                harvests_df = hfx.filter_data(harvests_df, "end_date", end_date)
            
            if not detailed_df.empty:
                detailed_df = hfx.filter_data(detailed_df, "years", years)
                detailed_df = hfx.filter_data(detailed_df, "months", months)
                detailed_df = hfx.filter_data(detailed_df, "customers", customers)
                detailed_df = hfx.filter_data(detailed_df, "start_date", start_date)
                detailed_df = hfx.filter_data(detailed_df, "end_date", end_date)
            
            # Display overview
            hfx.display_harvests_overview(harvests_df, detailed_df)
        
        with tab2:
            # Load combined data for list
            harvests_df = hfx.load_all_harvests_data()
            detailed_df = hfx.load_new_harvests_data()
            
            # Apply filters to both datasets
            if not harvests_df.empty:
                harvests_df = hfx.filter_data(harvests_df, "years", years)
                harvests_df = hfx.filter_data(harvests_df, "months", months)
                harvests_df = hfx.filter_data(harvests_df, "customers", customers)
                harvests_df = hfx.filter_data(harvests_df, "start_date", start_date)
                harvests_df = hfx.filter_data(harvests_df, "end_date", end_date)
            
            if not detailed_df.empty:
                detailed_df = hfx.filter_data(detailed_df, "years", years)
                detailed_df = hfx.filter_data(detailed_df, "months", months)
                detailed_df = hfx.filter_data(detailed_df, "customers", customers)
                detailed_df = hfx.filter_data(detailed_df, "start_date", start_date)
                detailed_df = hfx.filter_data(detailed_df, "end_date", end_date)
            
            # Display list with line performance
            hfx.display_harvests_list(harvests_df, detailed_df)
        
        with tab3:
            # Display harvest form
            hfx.create_harvest_form(current_user, customers_list)

    # ---- Logout ----
    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
