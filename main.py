import streamlit as st
import streamlit_authenticator as stauth
import yaml
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
    with st.sidebar:
        nav_bar = option_menu(
            st.session_state["name"],
            ["Dashboard", "Data Entry"],
            icons=["bar-chart-line", "clipboard-data"],
            menu_icon="person-circle",
        )

    if nav_bar == "Dashboard":
        dashboard_option = option_menu(
            menu_title=None,
            options= ["Sales Analysis", "Costs Analysis"],
            icons=["coin","card-text"],
            orientation="horizontal"
        
    )
        if dashboard_option == "Sales":
            st.write("Sales dashboard")
        if dashboard_option == "Costs":
            st.write("Costs dashboard")

    if nav_bar == "Data Entry":
        entry_option = option_menu(
            menu_title=None,
            options= ["Sales Form", "Costs Form"],
            icons=["journal-plus", "journal-minus"],
            orientation="horizontal"
        
    )
        if entry_option == "Sales":
            st.write("Sales Form")
        if entry_option == "Costs":
            st.write("Costs Form")

    authenticator.logout("Logout", "sidebar", key="unique_key")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
