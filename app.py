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
    st.title("🚀 Portfolio Tracker Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.header("Login")
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login"):
            success, user_tab = manager.login(u, p)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_tab = user_tab
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

# --- UI: MAIN DASHBOARD (LOGGED IN) ---
else:
    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title(f"👤 {st.session_state.user_tab.title}")
    menu = st.sidebar.radio("Navigation", ["My Portfolio", "Add Transaction", "Alerts"])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_tab = None
        st.rerun()

    # --- SECTION 1: MY PORTFOLIO ---
    if menu == "My Portfolio":
        st.title("📊 My Portfolio")
        try:
            data = st.session_state.user_tab.get_all_records()
            if data:
                st.write("Current Holdings:")
                st.table(data)
            else:
                st.info("Your portfolio is currently empty. Go to 'Add Transaction' to start!")
        except Exception as e:
            st.error(f"Error loading data: {e}")

    # --- SECTION 2: ADD TRANSACTION ---
    elif menu == "Add Transaction":
        st.title("➕ Add New Transaction")
        with st.form("transaction_form"):
            ticker = st.text_input("Ticker (e.g., AAPL, BTC)")
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
            price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
            date = st.date_input("Transaction Date")
            
            submitted = st.form_submit_button("Save to Portfolio")
            
            if submitted:
                if ticker:
                    try:
                        # Writing directly to the user's specific tab
                        st.session_state.user_tab.append_row([ticker.upper(), amount, price, str(date)])
                        st.success(f"Successfully added {ticker}!")
                    except Exception as e:
                        st.error(f"Failed to add: {e}")
                else:
                    st.warning("Please enter a ticker symbol.")

    # --- SECTION 3: ALERTS ---
    elif menu == "Alerts":
        st.title("🔔 Price Alerts")
        st.write("Set up notifications for your assets.")
        
        # This is where your old Alerts logic goes. 
        # Example structure:
        with st.form("alert_form"):
            alert_ticker = st.text_input("Ticker to watch")
            target_price = st.number_input("Target Price", min_value=0.0)
            alert_type = st.selectbox("Trigger when price is:", ["Above", "Below"])
            
            if st.form_submit_button("Set Alert"):
                # You can create a second tab for alerts or just append to the main tab with a label
                # For now, let's just show success:
                st.success(f"Alert set for {alert_ticker} at ${target_price}")
