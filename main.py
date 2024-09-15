import datetime

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from millify import millify
from pytz import timezone
from streamlit_option_menu import option_menu as option_menu

import cost_functions as cfx
import deposit_functions as dfx
import general_functions as gfx
import sales_functions as sfx
import withdraw_functions as wfx
import harvest_functions as hfx

gfx.set_page_config()

name, authentication_status, username, authenticator = gfx.auth()
if authentication_status:

    # # Define the scope
    # scope = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    #
    # # Load the credentials
    # creds = Credentials.from_service_account_file("", scopes=scope)
    #
    # # Connect to Google Sheets
    # client = gspread.authorize(creds)
    # # sheet = client.open("your_google_sheet_name").sheet1
    #
    # drive_service = build('drive', 'v3', credentials=creds)
    #
    # def upload_to_drive(file, file_name):
    #     file_metadata = {'name': file_name}
    #     media = MediaFileUpload(file_name, resumable=True, mimetype="image/png")
    #     file = drive_service.files().create(body=file,media_body=media, fields='id').execute()
    #     file_id = file.get('id')
    #     return f"https://drive.google.com/uc?id={file_id}"

    chrome_options = Options()
    # incognito window
    chrome_options.add_argument("--incognito")


    @st.experimental_dialog("Are you sure?")
    def user_surety():
        st.warning("Are you sure these numbers are correct?")
        col1, col2 = st.columns(2)

        with col1:
            yes_clicked = st.button("Yes", key="yes_button", use_container_width=True)
        with col2:
            no_clicked = st.button("No", key="no_button", use_container_width=True)

        if yes_clicked:
            return "yes"
        elif no_clicked:
            return "no"


    if 'date_range_toggle' not in st.session_state:
        st.session_state["date_range_toggle"] = False

    if 'nav_bar_selection' not in st.session_state:
        st.session_state["nav_bar_selection"] = "Costs"

    if 'quantity' not in st.session_state:
        st.session_state["quantity"] = 0

    if 'unit-price' not in st.session_state:
        st.session_state["unit-price"] = 0

    if 'total-price' not in st.session_state:
        st.session_state["total-price"] = 0


    def calculate_total_price():
        try:
            sale_quantity = int(st.session_state['quantity'])
            sale_unit_price = int(st.session_state['unit-price'])
            st.session_state["total-price"] = (sale_quantity * sale_unit_price)
            return sale_quantity * sale_unit_price
        except ValueError:
            return 0


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

        if current_user != "Victor Tindimwebwa":

            with details:

                if expenses_df.empty:
                    st.info("No records match the filtration criteria")
                    # st.stop()

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
            st.title(":red[Costs]")

            with st.form(key="costs"):
                c1, c2 = st.columns(2, vertical_alignment="bottom")
                c3, c4 = st.columns(2, vertical_alignment="bottom")
                c5, c6 = st.columns(2, vertical_alignment="bottom")
                c7, c8 = st.columns(2, vertical_alignment="bottom")

                with c1:
                    date = st.date_input("Date (dd/mm/yyyy)", value=datetime.datetime.now(), format="DD/MM/YYYY",
                                         max_value=datetime.datetime.now(),
                                         min_value=datetime.date(2022, 8, 1),
                                         )

                with c2:
                    category = st.selectbox(label="Category", index=None,
                                            options=cfx.get_cost_categories())

                with c3:
                    item = st.text_input(
                        placeholder="airtime",
                        label="Item",
                        disabled=False
                    )

                with c4:
                    cost_quantity = st.text_input(
                        label="Quantity",
                        disabled=False
                    )

                with c5:
                    unit_cost = st.text_input(
                        key="unit-cost",
                        placeholder="ugx",
                        label="Unit Cost",
                        disabled=False
                    )

                with c6:
                    total_cost = st.text_input(
                        placeholder="ugx",
                        label="Total Cost",
                        disabled=False
                    )

                with c7:
                    transport_cost = st.text_input(
                        placeholder="ugx",
                        label="Transport Cost (if any)",
                        disabled=False
                    )

                with c8:
                    transport_details = st.text_input(
                        placeholder="eg: from seeta to farm",
                        label="Transport Details (if any)",
                        disabled=False
                    )

                source_of_funds = st.selectbox("Source of Money", ["Bank", "Personal", "Sales"]
                if current_user == "Andrew" or current_user == "Tony" else ["Bank", "Sales"])

                cost_submitted = st.form_submit_button("Save")

                if cost_submitted:
                    timezone = timezone("Africa/Nairobi")

                    # amount_deposited = int(amount.strip())

                    timestamp = datetime.datetime.now(timezone).strftime(
                        "%d-%b-%Y %H:%M:%S" + " EAT"
                    )

                    data = [
                        timestamp,
                        date.strftime('%d/%m/%y'),
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
                        current_user
                    ]

                    with st.spinner("Saving cost data..."):
                        sheet_credentials = st.secrets["sheet_credentials"]
                        gc = gspread.service_account_from_dict(sheet_credentials)

                        pepper_workbook = gc.open_by_key(st.secrets["cost_sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Costs")

                        all_values = deposits_sheet.get_all_values()

                        next_row_index = len(all_values) + 1

                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )

                        st.success(
                            "✅ Cost saved Successfully"
                        )

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

        if current_user != "Victor Tindimwebwa":

            with sales_details:
                if final_sales_df.empty:
                    st.info("No records match the filtration criteria")
                    # st.stop()

                st.subheader("Sales by Customers")

                df_customers = final_sales_df["Customer"].unique()
                # df_customers = [str(customer) if pd.notnull(customer) else '' for customer in df_customers]
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
                                 alt.Tooltip("sum(Quantity Sold (kgs)):Q", title="Total Quantity Sold (kgs)",
                                             format=','),
                                 ]
                    )
                )

                st.altair_chart(bar, use_container_width=True)

        with sales_form:
            st.title(":green[Sales]")

            with st.form(key="sales"):
                x1, x2 = st.columns(2, vertical_alignment="bottom")
                x3, x4 = st.columns(2, vertical_alignment="bottom")
                x5, x6 = st.columns(2, vertical_alignment="bottom")
                x7, x8 = st.columns(2, vertical_alignment="bottom")

                with x1:
                    date = st.date_input("Date (dd/mm/yyyy)", value=datetime.datetime.now(), format="DD/MM/YYYY",
                                         max_value=datetime.datetime.now(),
                                         min_value=datetime.date(2022, 8, 1),
                                         )

                with x2:
                    customer = st.text_input(
                        placeholder="eg: vicky tindi",
                        label="Customer",
                        disabled=False
                    )

                with x3:
                    size = st.selectbox(label="Size", options=sfx.get_sizes())

                with x4:
                    unit = st.selectbox(label="Unit", options=sfx.get_units())

                with x5:
                    quantity = st.text_input(
                        value=1,
                        key="quantity",
                        placeholder="0",
                        label="Quantity",
                        disabled=False,
                        # help="Please enter a value greater than zero"
                    )

                with x6:
                    unit_price = st.text_input(
                        value=1,
                        key="unit-price",
                        placeholder="ugx",
                        label="Unit Price",
                        disabled=False,
                        # help="Please enter a value greater than zero"
                    )

                with x7:
                    total_price = st.number_input(
                        placeholder="ugx",
                        label="Total Price",
                        disabled=True,
                        value=calculate_total_price()

                    )

                with x8:
                    amount_paid = st.text_input(
                        key="amount_paid",
                        placeholder="0",
                        label="Amount Paid",
                        disabled=False,
                        # help="Please enter a value greater than zero"
                    )

                delivery_fee = st.text_input(
                    key="delivery",
                    placeholder="0",
                    label="Delivery Fee",
                    disabled=False,
                    # help="Please enter a value greater than zero"
                )

                sale_submitted = st.form_submit_button("Save", on_click=calculate_total_price)

                # payment_status = st.selectbox(label="Payment Status")

                if sale_submitted:
                    timezone = timezone("Africa/Nairobi")

                    # amount_deposited = int(amount.strip())

                    timestamp = datetime.datetime.now(timezone).strftime(
                        "%d-%b-%Y %H:%M:%S" + " EAT"
                    )

                    data = [
                        timestamp,
                        date.strftime('%d/%m/%y'),
                        customer,
                        size,
                        unit,
                        unit_price,
                        quantity,
                        st.session_state["total-price"],
                        "payment_status is being dropped",
                        amount_paid,
                        delivery_fee,
                        current_user
                    ]

                    with st.spinner("Saving sale data..."):
                        sheet_credentials = st.secrets["sheet_credentials"]
                        gc = gspread.service_account_from_dict(sheet_credentials)

                        pepper_workbook = gc.open_by_url(st.secrets["sales_sheet_key"])
                        deposits_sheet = pepper_workbook.worksheet("Final Sales")

                        all_values = deposits_sheet.get_all_values()

                        next_row_index = len(all_values) + 1

                        deposits_sheet.append_rows(
                            [data],
                            value_input_option="user_entered",
                            insert_data_option="insert_rows",
                            table_range=f"a{next_row_index}",
                        )

                        st.success(
                            "✅ Sale saved Successfully"
                        )

    elif nav_bar == "Deposits":
        deposits, deposit_form = st.tabs(["➕ Deposits", "📜 Form"])

        deposits_df = dfx.load_deposits()

        deposits_df = dfx.filter_data(deposits_df, 'years', years)
        deposits_df = dfx.filter_data(deposits_df, 'months', months)
        deposits_df = dfx.filter_data(deposits_df, 'start_date', start_date)
        deposits_df = dfx.filter_data(deposits_df, 'end_date', end_date)

        if current_user != "Victor Tindimwebwa":

            with deposits:

                if deposits_df.empty:
                    st.info("No records match the filtration criteria")
                    # st.stop()

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

                st.info("Uploading an image of the deposit slip will come in the next release!")

                # uploaded_image = st.file_uploader("Upload deposit slip", ['png', 'jpg', 'jpeg'])
                # if uploaded_image is not None:
                #     image_bytes = uploaded_image.getvalue()
                #     file_link = upload_to_drive(image_bytes, uploaded_image.name)

                # imageio = StringIO(uploaded_image.getvalue())
                # interim = imageio.decode("utf-8")
                # image = imageio.read()

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
                        int(amount),
                        current_user,
                        # file_link
                        # base64.b64encode(image_bytes).decode('utf-8')
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

        if current_user != "Victor Tindimwebwa":

            withdraws, withdraw_form = st.tabs(["➖ Withdraws", "📜 Form"])

            withdraw_df = wfx.load_withdraws()

            withdraw_df = wfx.filter_data(withdraw_df, 'years', years)
            withdraw_df = wfx.filter_data(withdraw_df, 'months', months)
            withdraw_df = wfx.filter_data(withdraw_df, 'start_date', start_date)
            withdraw_df = wfx.filter_data(withdraw_df, 'end_date', end_date)

            with withdraws:

                if withdraw_df.empty:
                    st.info("No records match the filtration criteria")
                    # st.stop()

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

                    reason_for_withdraw = st.text_input(
                        placeholder="reason for withdraw",
                        label="Reason for Withdraw",
                        disabled=False
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
                            int(amount),
                            reason_for_withdraw,
                            current_user
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

    elif nav_bar == "Harvests":
        harvests_df = hfx.get_harvests_df()
        st.dataframe(harvests_df, use_container_width=True)

    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
