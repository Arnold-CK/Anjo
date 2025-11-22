import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import pandas as pd

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


def load_customers_data():
    """Load full customer data with all attributes."""
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)
    pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
    customers_sheet = pepper_workbook.worksheet("Customers")

    # Pull into DataFrame
    customers_df = get_as_dataframe(customers_sheet, parse_dates=True)

    # Drop unnamed columns
    customers_df = customers_df.loc[:, ~customers_df.columns.str.contains('^Unnamed')]

    # Drop rows where 'Name' is missing
    df = customers_df.dropna(subset=["Name"]).copy()
    
    # Define expected columns
    expected_cols = ["Name", "Location", "Contact Person", "Phone Number", "Email"]
    
    # Ensure all expected columns exist
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    
    # Keep only expected columns
    df = df[expected_cols]
    
    # Clean up the data and replace NaN with empty strings
    df["Name"] = df["Name"].astype(str).str.strip().replace('nan', '')
    df["Location"] = df["Location"].astype(str).str.strip().replace('nan', '')
    df["Contact Person"] = df["Contact Person"].astype(str).str.strip().replace('nan', '')
    df["Phone Number"] = df["Phone Number"].astype(str).str.strip().replace('nan', '')
    df["Email"] = df["Email"].astype(str).str.strip().replace('nan', '')
    
    # Sort alphabetically by name (case-insensitive)
    df = df.sort_values(by="Name", key=lambda x: x.str.lower())
    
    return df


def display_customers_table():
    """Display customers in a formatted table."""
    st.subheader("📋 Customer Directory")
    
    customers_df = load_customers_data()
    
    if customers_df.empty:
        st.info("No customers found. Add your first customer using the form above!")
    else:
        st.dataframe(
            customers_df,
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn(
                    "👤 Customer Name",
                    width="large",
                ),
                "Location": st.column_config.TextColumn(
                    "📍 Location",
                    width="medium",
                ),
                "Contact Person": st.column_config.TextColumn(
                    "👥 Contact Person",
                    width="medium",
                ),
                "Phone Number": st.column_config.TextColumn(
                    "📞 Phone Number",
                    width="medium",
                ),
                "Email": st.column_config.TextColumn(
                    "📧 Email",
                    width="medium",
                ),
            },
            hide_index=True,
            height=400,
        )
        st.caption(f"Total Customers: {len(customers_df)}")


def create_customer_form():
    """Display a form to create a new customer and save it to Google Sheets."""
    st.subheader("➕ Add New Customer")
    
    with st.form("new_customer_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name *", placeholder="e.g., ABC Trading Ltd")
            contact_person = st.text_input("Contact Person *", placeholder="e.g., John Doe")
            phone_number = st.text_input("Phone Number *", placeholder="e.g., +256 700 123456")
        
        with col2:
            location = st.text_input("Location *", placeholder="e.g., Kampala, Uganda")
            email = st.text_input("Email", placeholder="e.g., contact@company.com")
        
        submit = st.form_submit_button("Add Customer", use_container_width=True)
        
        if submit:
            # Validate required fields
            if not all([customer_name, location, contact_person, phone_number]):
                st.error("❌ Please fill in all required fields")
            else:
                try:
                    # Connect to Google Sheets
                    sheet_credentials = st.secrets["sheet_credentials"]
                    gc = gspread.service_account_from_dict(sheet_credentials)
                    pepper_workbook = gc.open_by_key(st.secrets["sheet_key"])
                    customers_sheet = pepper_workbook.worksheet("Customers")
                    
                    # Create new customer data as dictionary matching column names
                    customer_data = {
                        "Name": customer_name.strip(),
                        "Location": location.strip(),
                        "Contact Person": contact_person.strip(),
                        "Phone Number": phone_number.strip(),
                        "Email": email.strip() if email else ""
                    }
                    
                    # Get next row index and write using set_with_dataframe
                    with st.spinner("Saving customer data..."):
                        all_values = customers_sheet.get_all_values()
                        next_row_index = len(all_values) + 1
                        
                        set_with_dataframe(
                            customers_sheet,
                            pd.DataFrame([customer_data]),
                            row=next_row_index,
                            include_column_header=False,
                            include_index=False,
                        )
                        st.success(f"✅ Customer '{customer_name}' added successfully!")
                        st.balloons()
                        # Trigger rerun to refresh the table
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error adding customer: {str(e)}")
