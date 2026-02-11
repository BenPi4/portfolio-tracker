import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from manager import PortfolioManager

# --- IMPORT LOGIC FROM HELPER FILE ---
# Make sure portfolio_logic.py is in the same folder
from portfolio_logic import (
    calculate_cash_balance,
    get_current_holdings,
    fetch_live_prices,
    build_portfolio_table,
    calculate_portfolio_metrics,
    calculate_historical_portfolio_value,
    get_sector_allocation
)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Pro Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE MANAGER ---
@st.cache_resource
def get_manager():
    """
    Initialize PortfolioManager using Streamlit Secrets or local file.
    """
    if "gcp_service_account" in st.secrets:
        return PortfolioManager(dict(st.secrets["gcp_service_account"]))
    
    if os.path.exists('credentials.json'):
        return PortfolioManager('credentials.json')
    
    st.error("Credentials not found. Please configure secrets or upload json.")
    st.stop()

manager = get_manager()

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_tab' not in st.session_state: st.session_state.user_tab = None
if 'alerts_tab' not in st.session_state: st.session_state.alerts_tab = None

# --- HELPER FUNCTIONS ---
def load_data():
    """Load transactions from the user's Google Sheet tab."""
    try:
        data = st.session_state.user_tab.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure required columns exist and convert types
        if not df.empty and 'Type' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        # If sheet is empty or headers are missing
        return pd.DataFrame()

def load_alerts():
    """Load alerts from the user's Alerts tab."""
    try:
        if st.session_state.alerts_tab:
            data = st.session_state.alerts_tab.get_all_records()
            return pd.DataFrame(data)
        return pd.DataFrame()
    except: return pd.DataFrame()

def add_alert_to_sheet(ticker, target, condition):
    """Add a new alert row to the Google Sheet."""
    try:
        if st.session_state.alerts_tab:
            st.session_state.alerts_tab.append_row([ticker, target, condition, "Yes"])
            st.cache_data.clear() # Refresh cache to show new data immediately
            return True
        else:
            st.error("Alerts tab not found. Please contact support.")
            return False
    except Exception as e:
        st.error(f"Error adding alert: {e}")
        return False

# ==========================================
#               MAIN APP LOGIC
# ==========================================

if not st.session_state.logged_in:
    # --- LOGIN SCREEN ---
    st.title("🚀 Portfolio Tracker Login")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login"):
            success, trans_tab, alerts_tab = manager.login(u, p)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_tab = trans_tab
                st.session_state.alerts_tab = alerts_tab
                st.success(f"Welcome back, {u}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        st.write("Create a new account to get your own portfolio sheets.")
        nu = st.text_input("Choose Username", key="reg_u")
        np = st.text_input("Choose Password", type="password", key="reg_p")
        ne = st.text_input("Email (Optional)", key="reg_e")
        if st.button("Sign Up"):
            success, msg = manager.sign_up(nu, np, ne)
            if success:
                st.success(msg)
            else:
                st.error(msg)

else:
    # --- LOGGED IN DASHBOARD ---
    
    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state.user_tab.title}")
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_tab = None
        st.session_state.alerts_tab = None
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("📝 Actions")

    # 1. ADD TRANSACTION WIDGET
    with st.sidebar.expander("➕ Add Transaction", expanded=True):
        type_ = st.selectbox("Type", ['Buy', 'Sell', 'Deposit', 'Withdraw'])
        date_ = st.date_input("Date")
        
        if type_ in ['Buy', 'Sell']:
            ticker_ = st.text_input("Ticker Symbol").upper()
            qty_ = st.number_input("Quantity", min_value=0.0, step=0.01)
            price_ = st.number_input("Price ($)", min_value=0.0, step=0.01)
        else:
            ticker_ = "CASH"
            qty_ = 1.0
            price_ = st.number_input("Amount ($)", min_value=0.0, step=0.01)
        
        if st.sidebar.button("Add Transaction", type="primary"):
            if type_ in ['Buy', 'Sell'] and not ticker_:
                st.error("Please enter a ticker.")
            else:
                st.session_state.user_tab.append_row([str(date_), ticker_, type_, qty_, price_])
                st.success("Transaction added!")
                st.rerun()

    # 2. SET ALERT WIDGET
    with st.sidebar.expander("🔔 Set Price Alert"):
        alert_ticker = st.text_input("Ticker").upper()
        alert_price = st.number_input("Target Price ($)", min_value=0.0)
        alert_cond = st.selectbox("Condition", ["Above", "Below"])
        
        if st.sidebar.button("Set Alert"):
            if add_alert_to_sheet(alert_ticker, alert_price, alert_cond):
                st.success(f"Alert set for {alert_ticker}!")
                st.rerun()

    # --- MAIN CONTENT AREA ---
    st.title("📈 Pro Portfolio Tracker")
    st.markdown("*Real-time analytics & insights*")
    
    # Load Data
    df = load_data()
    
    if df.empty:
        st.info("👋 Your portfolio is currently empty. Use the sidebar to add your first transaction!")
        st.stop()

    # Calculate Portfolio Logic
    cash = calculate_cash_balance(df)
    holdings = get_current_holdings(df)
    
    # Fetch Prices
    with st.spinner("Fetching live market data..."):
        prices = fetch_live_prices(holdings['Ticker'].unique().tolist())
    
    port_df = build_portfolio_table(holdings, prices, cash)
    metrics = calculate_portfolio_metrics(port_df, cash, df)

    # --- METRICS SECTION ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${metrics['total_portfolio_value']:,.2f}")
    c2.metric("Cash Balance", f"${metrics['cash_balance']:,.2f}")
    
    # Color logic for return
    delta_color = "normal" if metrics['total_return_dollars'] >= 0 else "inverse"
    c3.metric("Total Return", f"${metrics['total_return_dollars']:,.2f}", f"{metrics['total_return_pct']:.2f}%", delta_color=delta_color)
    c4.metric("Daily P&L", f"${metrics['daily_pnl']:,.2f}", delta_color=delta_color)

    st.divider()

    # --- HOLDINGS TABLE ---
    st.markdown("### 💼 Current Holdings")
    
    # Format the dataframe for cleaner display (2 decimal places)
    display_df = port_df.copy()
    
    st.dataframe(
        display_df.style.format({
            "Avg Buy Price": "${:,.2f}",
            "Current Price": "${:,.2f}",
            "Market Value": "${:,.2f}",
            "Daily Return %": "{:.2f}%",
            "Total Return %": "{:.2f}%",
            "% of Portfolio": "{:.2f}%",
            "Alpha vs SPY": "{:.2f}%"
        }),
        use_container_width=True,
        hide_index=True  # Hides the index column (0,1,2...)
    )

    # --- CHARTS SECTION ---
    st.markdown("### 📊 Analytics")
    col_charts_1, col_charts_2 = st.columns(2)
    
    with col_charts_1:
        st.markdown("**Allocation**")
        holdings_data = port_df[['Ticker', 'Market Value']].copy()
        fig_pie = px.pie(holdings_data, values='Market Value', names='Ticker', hole=0.4)
        
        # FIX: Legend at bottom, tight margins to prevent cutting off
        fig_pie.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=30, b=50, l=0, r=0),
            height=350
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_charts_2:
        st.markdown("**Historical Performance**")
        # Calculate history (last 365 days)
        start_date = datetime.now() - timedelta(days=365)
        hist_df = calculate_historical_portfolio_value(df, start_date)
        
        if not hist_df.empty:
            fig_hist = px.line(hist_df, x='Date', y='Portfolio_Return_%')
            fig_hist.update_layout(
                margin=dict(t=30, b=30, l=0, r=0), 
                height=350,
                xaxis_title=None,
                yaxis_title="Return (%)"
            )
            # Add line color
            fig_hist.update_traces(line_color='#1f77b4', line_width=2)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Not enough data for chart.")

    # --- ACTIVE ALERTS SECTION ---
    st.markdown("### 🔔 Active Alerts")
    alerts_df = load_alerts()
    
    if not alerts_df.empty:
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active alerts configured.")
