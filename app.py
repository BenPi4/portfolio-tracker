import streamlit as st
import os
from manager import PortfolioManager

# --- CONFIGURATION & INIT ---
@st.cache_resource
def get_manager():
    """
    Hybrid initialization: Prioritizes Streamlit Secrets (Cloud) over local files.
    """
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        return PortfolioManager(creds_info)
    
    creds_path = 'credentials.json'
    if os.path.exists(creds_path):
        return PortfolioManager(creds_path)
    
    st.error("Missing Credentials! Please add them to Streamlit Secrets or upload credentials.json.")
    st.stop()

manager = get_manager()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_tab' not in st.session_state:
    st.session_state.user_tab = None

# --- UI: LOGIN / SIGNUP ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.header("Login")
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login"):
            success, user_tab = manager.login(u, p)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_tab = user_tab # This is now a Worksheet object
                st.success(f"Welcome back, {u}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        st.header("Create Account")
        new_u = st.text_input("Choose Username", key="reg_u")
        new_p = st.text_input("Choose Password", type="password", key="reg_p")
        email = st.text_input("Email (for sharing)", key="reg_e")
        if st.button("Register"):
            success, msg = manager.sign_up(new_u, new_p, email)
            if success:
                st.success(msg)
            else:
                st.error(msg)

# --- UI: MAIN DASHBOARD ---
else:
    st.sidebar.title(f"Hello, {st.session_state.user_tab.title}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_tab = None
        st.rerun()

    st.title("My Portfolio Tracker")

    # EXAMPLE: Reading data from the user's specific tab
    try:
        # Since 'user_tab' is a Worksheet, we can call get_all_records() directly
        data = st.session_state.user_tab.get_all_records()
        if data:
            st.write("Your current holdings:")
            st.table(data)
        else:
            st.info("Your portfolio is currently empty. Start by adding transactions!")
            
            # Example: Adding a row (If your app has an input form)
            if st.button("Add Test Row"):
                st.session_state.user_tab.append_row(["BTC", "1", "50000"])
                st.success("Test row added! Refresh to see changes.")
                
    except Exception as e:
        st.error(f"Error loading your data: {e}")
