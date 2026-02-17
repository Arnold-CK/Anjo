import calendar
import datetime
from typing import List

import altair as alt
import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from pytz import timezone as tz

import sales_functions as sfx


@st.cache_data
def get_month_name_dict():
    return {i: month_name for i, month_name in enumerate(calendar.month_name) if i != 0}


def format_column(entry):
    return " ".join(word.capitalize() for word in entry.split("_"))


def format_date(input_date):
    # Convert the input string to a datetime object
    # date_object = datetime.strptime(input_date, '%d/%m/%y')

    # Format the datetime object as required (8/Oct/2023)
    formatted_date = input_date.strftime("%d/%b/%Y")

    return formatted_date


def clean_harvests_df(repeated_harvests_df, customers_harvest_df):

    repeated_harvests_df["data-structures_repeat-size_small-quantity_small_size"] = (
        pd.to_numeric(
            repeated_harvests_df[
                "data-structures_repeat-size_small-quantity_small_size"
            ],
            errors="coerce",
        ).fillna(0)
    )

    repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"] = (
        pd.to_numeric(
            repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"],
            errors="coerce",
        ).fillna(0)
    )

    # Now you can safely sum the two columns to create the 'Quantity' column
    repeated_harvests_df["Quantity"] = (
        repeated_harvests_df["data-structures_repeat-size_small-quantity_small_size"]
        + repeated_harvests_df["data-structures_repeat-size_big-quantity_big_size"]
    )

    # Rename columns for clarity
    repeated_harvests_df.rename(
        columns={
            "data-structures_repeat-structure_name": "Structure",
            "PARENT_KEY": "InstanceID",
        },
        inplace=True,
    )

    customers_harvest_df.rename(
        columns={
            "data-bio_data-date": "Date",
            "data-bio_data-client_name": "Customer",
            "data-bio_data-entered_by": "Entered By",
            "data-meta-instanceID": "InstanceID",
        },
        inplace=True,
    )

    # Merge the two DataFrames on the 'InstanceID'
    final_df = pd.merge(customers_harvest_df, repeated_harvests_df, on="InstanceID")

    # Select the relevant columns for the final DataFrame
    final_df = final_df[
        ["Date", "Customer", "Structure", "Quantity", "Entered By"]
    ].dropna()
    final_df["Date"] = pd.to_datetime(final_df["Date"], format="%d/%m/%y")

    final_df = final_df.sort_values(by="Date", ascending=False)

    final_df["Date"] = final_df["Date"].apply(format_date)
    final_df.set_index("Date", inplace=True)

    return final_df


def process_customer(sales_df, customer):
    customer_df = sales_df[sales_df["Customer"] == customer]
    customer_df = customer_df.sort_values(by="Date", ascending=False)
    customer_df["Date"] = customer_df["Date"].apply(format_date)

    customer_df = customer_df.reset_index(drop=True)
    customer_df.index += 1

    return customer_df


def display_expander(customer, customer_df):
    total_qty = customer_df["Quantity"].sum()
    total_money = customer_df["Total Price"].sum()
    formatted_total_money = "{:,.0f}".format(total_money)

    with st.expander(f"{customer} - {total_qty} kg - {formatted_total_money} ugx"):
        st.dataframe(customer_df, use_container_width=True)


def filter_data(
    data: pd.DataFrame, filter_name: str, values: List[str]
) -> pd.DataFrame:
    if not values:
        return data

    if filter_name == "years":
        data = data[data["Date"].dt.year.isin(values)]

    if filter_name == "months":
        data = data[data["Date"].dt.month.isin(values)]

    if filter_name == "customers":
        data = data[data["Customer"].isin(values)]

    if filter_name == "start_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(
            date_string, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
        data = data[data["Date"] >= formatted_start_date]

    if filter_name == "end_date":
        date_string = str(values)
        formatted_start_date = datetime.datetime.strptime(
            date_string, "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
        data = data[data["Date"] <= formatted_start_date]

    return data


def convert_date_range(date_tuple):
    converted_dates = []
    for date_str in date_tuple:
        date_object = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
        converted_date = date_object.strftime("%d/%m/%y")
        converted_dates.append(converted_date)
    return converted_dates


def get_harvests_df():
    repeated_harvests_df, customers_harvests_df = load_harvests_df()
    final_harvests_df = clean_harvests_df(repeated_harvests_df, customers_harvests_df)

    return final_harvests_df


def load_harvests_df():
    sheet_credentials = st.secrets["sheet_credentials"]
    gc = gspread.service_account_from_dict(sheet_credentials)

    anjo_harvests_workbook = gc.open_by_url(st.secrets["harvest_sheet_key"])

    repeated_harvests_sheet = anjo_harvests_workbook.worksheet("data-structures_repeat")
    repeated_harvests_df = get_as_dataframe(repeated_harvests_sheet, parse_dates=True)

    customer_harvests_sheet = anjo_harvests_workbook.worksheet("Sheet1")
    customer_harvests_df = get_as_dataframe(customer_harvests_sheet, parse_dates=True)

    return repeated_harvests_df, customer_harvests_df


def get_units():
    units = ["kg"]

    units.sort()

    return units


def get_sizes():
    sizes = ["big", "small"]

    sizes.sort()

    return sizes


# ============= NEW HARVEST FUNCTIONS =============

def get_greenhouses():
    """Return list of greenhouse options."""
    return ["Structure A", "Structure B", "Structure C", "Structure D", "Structure E", "Structure F"]


def load_new_harvests_data():
    """Load harvest data from 'Final Harvests' worksheet with line details."""
    try:
        sheet_credentials = st.secrets["sheet_credentials"]
        gc = gspread.service_account_from_dict(sheet_credentials)
        anjo_harvests_workbook = gc.open_by_url(st.secrets["harvest_sheet_key"])
        
        # Try to get the worksheet, return empty if doesn't exist
        try:
            final_harvests_sheet = anjo_harvests_workbook.worksheet("Final Harvests")
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame()
        
        harvests_df = get_as_dataframe(final_harvests_sheet, parse_dates=True)
        
        # Rename columns based on actual sheet structure
        # Structure: Timestamp | Date of harvest | Quantity harvested in kgs (Line1) | 
        #            Unnamed:3-10 (Lines 2-9) | Unnamed:11 (Total) | Customer/Destination | Greenhouse
        column_renames = {}
        
        # Rename "Quantity harvested in kgs" to Line_1
        if 'Quantity harvested in kgs' in harvests_df.columns:
            column_renames['Quantity harvested in kgs'] = 'Line_1'
        
        # Lines 2-9 are in Unnamed: 3 through Unnamed: 10
        for i in range(3, 11):
            col_name = f'Unnamed: {i}'
            if col_name in harvests_df.columns:
                column_renames[col_name] = f'Line_{i-1}'  # Line_2 through Line_9
        
        # Total is in Unnamed: 11
        if 'Unnamed: 11' in harvests_df.columns:
            column_renames['Unnamed: 11'] = 'Total'
        
        # Standard column renames
        if 'Date of harvest' in harvests_df.columns:
            column_renames['Date of harvest'] = 'Date'
        if 'Customer/Destination' in harvests_df.columns:
            column_renames['Customer/Destination'] = 'Customer'
        
        harvests_df.rename(columns=column_renames, inplace=True)
        
        # Keep only the columns we need
        required_cols = ['Timestamp', 'Date', 'Line_1', 'Line_2', 'Line_3', 'Line_4', 
                        'Line_5', 'Line_6', 'Line_7', 'Line_8', 'Line_9', 'Total', 
                        'Customer', 'Greenhouse']
        available_cols = [col for col in required_cols if col in harvests_df.columns]
        harvests_df = harvests_df[available_cols]
        
        # Check if Date column exists (after renaming)
        if "Date" not in harvests_df.columns:
            return pd.DataFrame()
        
        # Drop rows where Date is missing
        harvests_df = harvests_df.dropna(subset=["Date"]).copy()
        
        # If no data, return empty DataFrame
        if harvests_df.empty:
            return pd.DataFrame()
        
        # Parse date with flexible format handling
        # pd.to_datetime with dayfirst=True will handle both dd/mm/yyyy and dd/mm/yy
        harvests_df["Date"] = pd.to_datetime(harvests_df["Date"], dayfirst=True, errors='coerce')
        
        # Ensure line columns exist and are numeric
        for i in range(1, 10):
            col = f"Line_{i}"
            if col not in harvests_df.columns:
                harvests_df[col] = 0
            harvests_df[col] = pd.to_numeric(harvests_df[col], errors="coerce").fillna(0)
        
        # Handle Total column - clean text like "40 KGS", "62KGS" before parsing
        if "Total" in harvests_df.columns:
            # Remove "KGS", "KG", spaces, and convert to numeric
            harvests_df["Total"] = harvests_df["Total"].astype(str).str.replace(r'\s*KG[S]?\s*', '', case=False, regex=True)
            harvests_df["Total"] = pd.to_numeric(harvests_df["Total"], errors="coerce").fillna(0)
        else:
            # Calculate total from lines if not present
            harvests_df["Total"] = sum(harvests_df[f"Line_{i}"] for i in range(1, 10))
        
        return harvests_df
        
    except Exception:
        return pd.DataFrame()


def load_all_harvests_data():
    """Load and combine harvest data from old and new worksheets."""
    combined_data = []
    
    # Load old data (silently fail if issues)
    try:
        old_df = get_harvests_df()
        if not old_df.empty:
            # Reset index to get Date as column
            old_df = old_df.reset_index()
            # Parse date
            old_df["Date"] = pd.to_datetime(old_df["Date"], format="%d/%b/%Y")
            # Rename Structure to match, Quantity is already named correctly
            old_df = old_df[["Date", "Customer", "Structure", "Quantity", "Entered By"]].copy()
            combined_data.append(old_df)
    except Exception:
        pass
    
    # Load new data (silently fail if issues)
    try:
        new_df = load_new_harvests_data()
        
        if not new_df.empty:
            # Rename columns to match old format
            new_df_simplified = new_df.copy()
            
            if "Greenhouse" in new_df_simplified.columns:
                new_df_simplified["Structure"] = new_df_simplified["Greenhouse"]
            if "Total" in new_df_simplified.columns:
                new_df_simplified["Quantity"] = new_df_simplified["Total"]
            if "Entered_By" in new_df_simplified.columns:
                new_df_simplified["Entered By"] = new_df_simplified["Entered_By"]
            
            # Select only the columns we need
            available_cols = [col for col in ["Date", "Customer", "Structure", "Quantity", "Entered By"] if col in new_df_simplified.columns]
            new_df_simplified = new_df_simplified[available_cols].copy()
            
            combined_data.append(new_df_simplified)
    except Exception:
        pass
    
    # Combine all data
    if combined_data:
        final_df = pd.concat(combined_data, ignore_index=True)
        final_df = final_df.sort_values(by="Date", ascending=False)
        return final_df
    else:
        return pd.DataFrame()


def create_harvest_form(current_user, customers_list):
    """Display form to create a new harvest entry."""
    st.subheader("➕ Add New Harvest")
    
    # Entry method selection OUTSIDE the form so it responds immediately
    entry_method = st.radio(
        "How would you like to enter harvest data?",
        options=["Enter by individual lines", "Enter total harvest only"],
        horizontal=True,
        key="harvest_entry_method"
    )
    
    st.divider()
    
    with st.form("new_harvest_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date = st.date_input(
                "Date of Harvest",
                value=datetime.datetime.now(),
                format="DD/MM/YYYY",
                max_value=datetime.datetime.now(),
                min_value=datetime.date(2022, 8, 1),
            )
        
        with col2:
            customer = st.selectbox(
                label="Customer/Destination",
                options=customers_list,
                placeholder="Select Customer",
                index=None,
            )
        
        with col3:
            greenhouse = st.selectbox(
                label="Greenhouse",
                options=get_greenhouses(),
                placeholder="Select Greenhouse",
                index=None,
            )
        
        st.divider()
        
        line_values = [0.0] * 9  # Initialize with zeros
        total = 0.0
        
        if entry_method == "Enter by individual lines":
            st.write("**Quantity Harvested per Line (kg)**")
            
            # Create 9 line inputs in 3 rows of 3
            line_values = []
            for row in range(3):
                cols = st.columns(3)
                for col_idx in range(3):
                    line_num = row * 3 + col_idx + 1
                    with cols[col_idx]:
                        value = st.number_input(
                            f"Line {line_num}",
                            min_value=0.0,
                            value=0.0,
                            step=0.1,
                            key=f"harvest_line_{line_num}"
                        )
                        line_values.append(value)
            
            # Calculate total from lines
            total = sum(line_values)
            st.markdown(f"**Total Volume: {total:.1f} kg**")
            
        else:  # Enter total directly
            st.write("**Total Quantity Harvested (kg)**")
            total = st.number_input(
                "Total Harvest",
                min_value=0.0,
                value=0.0,
                step=0.1,
                key="harvest_total_direct"
            )
            st.info("💡 Line-by-line data will be empty for this entry")
        
        submit = st.form_submit_button("Submit Harvest", use_container_width=True)
        
        if submit:
            # Validate required fields
            if not all([customer, greenhouse, date]):
                st.error("❌ Please fill in Date, Customer, and Greenhouse")
            elif total == 0:
                st.error("❌ Total volume must be greater than 0")
            else:
                try:
                    # Connect to Google Sheets
                    sheet_credentials = st.secrets["sheet_credentials"]
                    gc = gspread.service_account_from_dict(sheet_credentials)
                    anjo_harvests_workbook = gc.open_by_url(st.secrets["harvest_sheet_key"])
                    final_harvests_sheet = anjo_harvests_workbook.worksheet("Final Harvests")
                    
                    # Create timestamp
                    tz_eat = tz("Africa/Nairobi")
                    timestamp = datetime.datetime.now(tz_eat).strftime("%d-%b-%Y %H:%M:%S EAT")
                    
                    # Format date
                    formatted_date = date.strftime("%d/%m/%y")
                    
                    # Prepare data matching the sheet structure:
                    # Timestamp | Date of harvest | Quantity harvested in kgs (Line1) | 
                    # Unnamed:3-10 (Lines 2-9) | Unnamed:11 (Total) | Customer/Destination | Greenhouse
                    
                    # Create DataFrame with columns in correct order
                    harvest_data = pd.DataFrame([{
                        "Timestamp": timestamp,
                        "Date of harvest": formatted_date,
                        "Quantity harvested in kgs": line_values[0] if line_values else 0,  # Line_1
                        "1": line_values[1] if line_values else 0,  # Line_2
                        "2": line_values[2] if line_values else 0,  # Line_3
                        "3": line_values[3] if line_values else 0,  # Line_4
                        "4": line_values[4] if line_values else 0,  # Line_5
                        "5": line_values[5] if line_values else 0,  # Line_6
                        "6": line_values[6] if line_values else 0,  # Line_7
                        "7": line_values[7] if line_values else 0,  # Line_8
                        "8": line_values[8] if line_values else 0,  # Line_9
                        "Total": total,  # Write as number for easier parsing
                        "Customer/Destination": customer,
                        "Greenhouse": greenhouse,
                    }])
                    
                    # Write to Google Sheets (data starts at row 3)
                    with st.spinner("Saving harvest data..."):
                        all_values = final_harvests_sheet.get_all_values()
                        # Since data starts at row 3, next_row_index should be len(all_values) + 1
                        # But if sheet is empty or only has headers, we want to write at row 3
                        next_row_index = max(3, len(all_values) + 1)
                        
                        set_with_dataframe(
                            final_harvests_sheet,
                            harvest_data,
                            row=next_row_index,
                            include_column_header=False,
                            include_index=False,
                        )
                        st.success("✅ Harvest saved successfully!")
                        st.balloons()
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving harvest: {str(e)}")


def display_harvests_list(harvests_df, detailed_df=None):
    """Display harvest events in a table."""
    if harvests_df.empty:
        st.info("No harvest records found. Add your first harvest using the form!")
        return
    
    # Show count at the top
    total_harvests = len(harvests_df)
    total_volume = harvests_df["Quantity"].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Harvest Events", f"{total_harvests}")
    with col2:
        st.metric("Total Volume Harvested", f"{total_volume:,.1f} kg")
    
    st.divider()
    st.subheader("📋 Harvest Records")
    
    # Format the dataframe for display
    display_df = harvests_df.copy()
    display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime("%d/%b/%Y")
    display_df["Quantity"] = display_df["Quantity"].apply(lambda x: f"{x:,.1f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "Date": st.column_config.TextColumn("📅 Date", width="medium"),
            "Customer": st.column_config.TextColumn("👤 Customer", width="large"),
            "Structure": st.column_config.TextColumn("🏠 Greenhouse", width="small"),
            "Quantity": st.column_config.TextColumn("⚖️ Volume (kg)", width="medium"),
            "Entered By": st.column_config.TextColumn("✍️ Entered By", width="medium"),
        },
        hide_index=True,
        height=500,
    )


def analyze_line_performance(detailed_df):
    """Analyze performance of individual lines from detailed harvest data, grouped by structure."""
    if detailed_df.empty:
        return pd.DataFrame()
    
    # Check if Greenhouse column exists
    if "Greenhouse" not in detailed_df.columns:
        return pd.DataFrame()
    
    line_data = []
    
    # Get unique structures/greenhouses
    structures = detailed_df["Greenhouse"].unique()
    
    for structure in structures:
        structure_df = detailed_df[detailed_df["Greenhouse"] == structure]
        
        for i in range(1, 10):
            col = f"Line_{i}"
            if col in structure_df.columns:
                line_values = pd.to_numeric(structure_df[col], errors="coerce").fillna(0)
                non_zero_values = line_values[line_values > 0]
                if len(non_zero_values) > 0:
                    line_data.append({
                        "Structure": structure,
                        "Line": f"Line {i}",
                        "Avg_Volume": non_zero_values.mean(),
                        "Harvest_Count": len(non_zero_values),
                        "Total_Volume": non_zero_values.sum()
                    })
    
    if line_data:
        return pd.DataFrame(line_data).sort_values(["Structure", "Avg_Volume"], ascending=[True, False])
    else:
        return pd.DataFrame()


def display_harvests_overview(harvests_df, detailed_df):
    """Display harvest overview with KPIs and charts."""
    if harvests_df.empty:
        st.info("No harvest data available for the selected filters")
        return
    
    # Load sales data for comparison
    try:
        sales_df = sfx.get_sales_df()
        
        # Filter sales data to match the same date range as harvest data
        if not sales_df.empty and "Date" in sales_df.columns:
            min_harvest_date = harvests_df["Date"].min()
            max_harvest_date = harvests_df["Date"].max()
            sales_df["Date"] = pd.to_datetime(sales_df["Date"])
            sales_df = sales_df[(sales_df["Date"] >= min_harvest_date) & (sales_df["Date"] <= max_harvest_date)]
            total_sold = sales_df["Quantity"].sum()
        else:
            total_sold = 0
    except Exception:
        total_sold = 0
    
    # Calculate totals
    total_harvested = harvests_df["Quantity"].sum()
    stock_balance = total_harvested - total_sold
    
    # Top Row: Harvest vs Sales Comparison
    st.subheader("📊 Harvest vs Sales")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🌱 Total Harvested", f"{total_harvested:,.1f} kg")
    
    with col2:
        st.metric("💰 Total Sold", f"{total_sold:,.1f} kg")
    
    with col3:
        stock_color = "normal" if stock_balance >= 0 else "inverse"
        st.metric("📦 Stock Balance", f"{stock_balance:,.1f} kg", 
                 delta=f"{(stock_balance/total_harvested*100):.1f}% of harvest" if total_harvested > 0 else None)
    
    st.divider()
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_events = len(harvests_df)
        st.metric("Total Harvests", f"{total_events}")
    
    with col2:
        st.metric("Harvest Volume", f"{total_harvested:,.1f} kg")
    
    with col3:
        avg_volume = harvests_df["Quantity"].mean()
        st.metric("Avg per Harvest", f"{avg_volume:,.1f} kg")
    
    with col4:
        active_structures = harvests_df["Structure"].nunique()
        st.metric("Active Greenhouses", f"{active_structures}")
    
    st.divider()
    
    # Charts Section
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Trend Chart
        st.subheader("📈 Harvest Trends")
        if len(harvests_df) > 0:
            trend_df = harvests_df.copy()
            trend_df["Date"] = pd.to_datetime(trend_df["Date"])
            daily_volumes = trend_df.groupby("Date")["Quantity"].sum().reset_index()
            daily_volumes.columns = ["Date", "Volume"]
            
            chart = alt.Chart(daily_volumes).mark_area(
                interpolate="monotone",
                opacity=0.3,
                color="#2ca02c",
                line={"color": "#1f7a1f", "strokeWidth": 3}
            ).encode(
                x=alt.X("Date:T", title="Date", axis=alt.Axis(grid=False, labelAngle=-45)),
                y=alt.Y("Volume:Q", title="Volume (kg)", axis=alt.Axis(grid=False, format=".2s")),
                tooltip=[
                    alt.Tooltip("Date:T", title="Date", format="%d %b %Y"),
                    alt.Tooltip("Volume:Q", title="Volume", format=",.1f")
                ]
            ).properties(height=300)
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Not enough data for trend chart")
    
    with col_right:
        # Top Structures
        st.subheader("🏆 Top Greenhouses")
        structure_performance = harvests_df.groupby("Structure")["Quantity"].sum().reset_index()
        structure_performance.columns = ["Greenhouse", "Total Volume"]
        structure_performance = structure_performance.sort_values("Total Volume", ascending=False).head(6)
        
        chart = alt.Chart(structure_performance).mark_bar().encode(
            x=alt.X("Total Volume:Q", title="Total Volume (kg)"),
            y=alt.Y("Greenhouse:N", sort="-x", title="Greenhouse"),
            color=alt.value("#1f77b4"),
            tooltip=["Greenhouse", alt.Tooltip("Total Volume:Q", format=",.1f")]
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
    
    st.divider()
    
    # Line Performance Analysis (new data only)
    if not detailed_df.empty:
        st.subheader("📊 Line Performance Analysis by Structure")
        st.info("💡 **Why Track Each Line?** Each line can have different conditions (microclimate) - like temperature, sunlight, or water flow. For example, Line 1 near the door might get more airflow while Line 9 is warmer. By tracking yields per line, you can spot which areas produce best and focus your planting and care on the strongest zones. You can also make changes to improve weaker lines - like adjusting ventilation or shade - to match the performance of your top line.")
        line_perf = analyze_line_performance(detailed_df)
        
        if not line_perf.empty:
            # Group by structure and display in expanders
            structures = sorted(line_perf["Structure"].unique())
            
            for structure in structures:
                with st.expander(f"🏠 Greenhouse {structure}", expanded=False):
                    structure_data = line_perf[line_perf["Structure"] == structure]
                    
                    col_line1, col_line2 = st.columns([2, 1])
                    
                    with col_line1:
                        chart = alt.Chart(structure_data).mark_bar().encode(
                            x=alt.X("Avg_Volume:Q", title="Average Volume (kg)"),
                            y=alt.Y("Line:N", sort="-x", title="Line Number"),
                            color=alt.value("#2ca02c"),
                            tooltip=[
                                "Line", 
                                alt.Tooltip("Avg_Volume:Q", format=".1f", title="Avg Volume (kg)"), 
                                alt.Tooltip("Harvest_Count:Q", title="Times Harvested"),
                                alt.Tooltip("Total_Volume:Q", format=".1f", title="Total Volume (kg)")
                            ]
                        ).properties(height=250)
                        
                        st.altair_chart(chart, use_container_width=True)
                    
                    with col_line2:
                        display_data = structure_data[["Line", "Avg_Volume", "Total_Volume", "Harvest_Count"]].copy()
                        st.dataframe(
                            display_data.style.format({
                                "Avg_Volume": "{:.1f}",
                                "Total_Volume": "{:.1f}"
                            }),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Line": "Line",
                                "Avg_Volume": "Avg (kg)",
                                "Total_Volume": "Total (kg)",
                                "Harvest_Count": "Count"
                            }
                        )
        else:
            st.info("No line-level data available yet")
