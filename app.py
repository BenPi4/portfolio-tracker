import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import os

# --- IMPORT THE MANAGER ---
from manager import PortfolioManager 

# Import calculation logic (Assuming this file exists in your folder)
from portfolio_logic import (
    calculate_cash_balance,
    get_current_holdings,
    fetch_live_prices,
    build_portfolio_table,
    calculate_portfolio_metrics,
    calculate_historical_portfolio_value,
    get_sector_allocation
)

# Page configuration
st.set_page_config(
    page_title="Pro Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { padding: 0rem 1rem; }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; }
    h1 { color: #1f77b4; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)


# --- Authentication & Setup ---

@st.cache_resource
def get_manager():
    """
    Hybrid initialization: Prioritizes Streamlit Secrets (Cloud) over local files.
    """
    # בדיקה אם יש נתונים ב-Secrets (הדרך הבטוחה לענן)
    if "gcp_service_account" in st.secrets:
        # אנחנו הופכים את ה-Secrets למילון רגיל ושולחים ל-Manager
        creds_info = dict(st.secrets["gcp_service_account"])
        return PortfolioManager(creds_info)
    
    # אם אין Secrets, רק אז נחפש קובץ פיזי (למצב פיתוח ב-Codespace)
    creds_path = 'credentials.json'
    if os.path.exists(creds_path):
        return PortfolioManager(creds_path)
    
    st.error("Missing Credentials! Please add them to Streamlit Secrets or upload credentials.json.")
    st.stop()

def login_page():
    """Display the login AND sign-up screen."""
    st.markdown("<h1 style='text-align: center;'>🔐 Portfolio Portal</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Create Tabs for Login and Sign Up
        tab1, tab2 = st.tabs(["Login", "Sign Up (New User)"])
        
        manager = get_manager()
        
        # --- TAB 1: LOGIN ---
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted:
                    with st.spinner("Verifying credentials..."):
                        success, sheet_obj = manager.login(username, password)
                        
                        if success:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.session_state['sheet_id'] = sheet_obj.id # Save the ID!
                            st.success(f"Welcome back, {username}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Incorrect username or password.")

        # --- TAB 2: SIGN UP ---
        with tab2:
            st.warning("New here? Create your own private portfolio sheet.")
            with st.form("signup_form"):
                new_user = st.text_input("Choose Username")
                new_pass = st.text_input("Choose Password", type="password")
                email = st.text_input("Email (Optional - to share sheet)", placeholder="user@gmail.com")
                signup_submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if signup_submitted:
                    if len(new_user) < 3 or len(new_pass) < 4:
                        st.error("Username/Password too short.")
                    else:
                        with st.spinner("Creating your environment (this takes about 5 seconds)..."):
                            success, msg = manager.sign_up(new_user, new_pass, email)
                            if success:
                                st.success(msg)
                                st.info("You can now go to the 'Login' tab and sign in!")
                            else:
                                st.error(msg)

# --- Data Loading Functions ---

@st.cache_data(ttl=60)
def load_transactions(_manager, sheet_id):
    """Load transactions using the Manager's client and specific Sheet ID."""
    try:
        # We use the manager's internal client to open the sheet by ID
        spreadsheet = _manager.client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Transactions')
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
        return pd.DataFrame()

def add_transaction(_manager, sheet_id, transaction_data):
    try:
        spreadsheet = _manager.client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Transactions')
        worksheet.append_row([
            transaction_data['Date'].strftime('%Y-%m-%d'),
            transaction_data['Ticker'],
            transaction_data['Type'],
            transaction_data['Quantity'],
            transaction_data['Price']
        ])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- Chart Functions (Unchanged) ---
def create_performance_chart(historical_df, timeframe):
    if historical_df.empty: return None
    today = datetime.now()
    if timeframe == '1W': start = today - timedelta(days=7)
    elif timeframe == '1M': start = today - timedelta(days=30)
    elif timeframe == 'YTD': start = datetime(today.year, 1, 1)
    elif timeframe == '1Y': start = today - timedelta(days=365)
    else: start = historical_df['Date'].min()
    
    filtered_df = historical_df[historical_df['Date'] >= start].copy()
    if filtered_df.empty: return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df['Portfolio_Return_%'], mode='lines', name='Portfolio', line=dict(color='#1f77b4', width=3)))
    fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df['SPY_Return_%'], mode='lines', name='S&P 500', line=dict(color='#ff7f0e', width=2, dash='dash')))
    fig.update_layout(title='Performance vs S&P 500', xaxis_title='Date', yaxis_title='Return (%)', hovermode='x unified', height=400, legend=dict(orientation="h", y=1.02, x=1))
    return fig

def create_allocation_charts(portfolio_df, cash_balance):
    if portfolio_df.empty: return None, None
    holdings = portfolio_df[['Ticker', 'Market Value']].copy()
    if cash_balance > 0:
        holdings = pd.concat([holdings, pd.DataFrame([{'Ticker': 'CASH', 'Market Value': cash_balance}])])
    
    fig_holdings = px.pie(holdings, values='Market Value', names='Ticker', title='Holdings', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
    fig_holdings.update_traces(textposition='inside', textinfo='percent+label')
    fig_holdings.update_layout(margin=dict(l=20,r=20,t=40,b=20), height=350, showlegend=False)

    sector_data = get_sector_allocation(portfolio_df)
    if not sector_data.empty:
        fig_sector = px.pie(sector_data, values='Value', names='Sector', title='Sectors', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sector.update_traces(textposition='inside', textinfo='percent+label')
        fig_sector.update_layout(margin=dict(l=20,r=20,t=40,b=20), height=350, showlegend=False)
    else:
        fig_sector = None
    return fig_holdings, fig_sector

# --- Main App Logic ---

def main_app():
    """The actual dashboard, only shown after login."""
    
    # Logout Button in Sidebar
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state['username']}**")
        if st.button("Logout", type="secondary"):
            for key in ['logged_in', 'username', 'sheet_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.divider()

    # Get the manager and the current user's sheet ID
    manager = get_manager()
    sheet_id = st.session_state['sheet_id']
    
    # Title
    st.title(f"📈 Portfolio: {st.session_state['username'].capitalize()}")

    # Sidebar - Add Transaction
    st.sidebar.header("📝 Actions")
    with st.sidebar.expander("➕ Add Transaction", expanded=False):
        t_type = st.selectbox("Type", ['Buy', 'Sell', 'Deposit Cash', 'Withdraw Cash'])
        t_date = st.date_input("Date", value=datetime.now())
        if t_type in ['Buy', 'Sell']:
            ticker = st.text_input("Ticker", "").upper()
            qty = st.number_input("Qty", 0.0, step=0.01)
            price = st.number_input("Price", 0.0, step=0.01)
        else:
            ticker = 'CASH'
            qty = 1.0
            price = st.number_input("Amount", 0.0, step=0.01)
            
        if st.button("Submit Transaction"):
            data = {'Date': t_date, 'Ticker': ticker, 'Type': t_type, 'Quantity': qty, 'Price': price}
            if add_transaction(manager, sheet_id, data):
                st.success("Added!")
                time.sleep(0.5)
                st.rerun()

    # Load Data
    with st.spinner("Loading your personal data..."):
        transactions_df = load_transactions(manager, sheet_id)
    
    if transactions_df.empty:
        st.info("👋 Welcome! Your portfolio sheet is empty. Add a transaction to start.")
        return

    # Calculations
    cash = calculate_cash_balance(transactions_df)
    holdings = get_current_holdings(transactions_df)
    
    tickers = []
    if not holdings.empty:
        tickers = holdings['Ticker'].unique().tolist()
    
    with st.spinner("Fetching market data..."):
        prices = fetch_live_prices(tickers)
        
    portfolio = build_portfolio_table(holdings, prices, cash)
    metrics = calculate_portfolio_metrics(portfolio, cash, transactions_df)
    
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${metrics['total_portfolio_value']:,.2f}")
    c2.metric("Cash", f"${metrics['cash_balance']:,.2f}")
    c3.metric("Return", f"${metrics['total_return_dollars']:,.2f}", f"{metrics['total_return_pct']:.2f}%")
    c4.metric("Daily P&L", f"${metrics['daily_pnl']:,.2f}")
    
    # Table
    st.subheader("💼 Holdings")
    if not portfolio.empty:
        disp = portfolio.copy()
        for c in ['Avg Buy Price', 'Current Price', 'Market Value']:
            disp[c] = disp[c].apply(lambda x: f"${x:,.2f}")
        for c in ['% of Portfolio', 'Total Return %', 'Daily Return %', 'Alpha vs SPY']:
            disp[c] = disp[c].apply(lambda x: f"{x:.2f}%")
        st.dataframe(disp, use_container_width=True, hide_index=True)
    
    # Historical Chart
    st.subheader("📈 Performance")
    tf = st.selectbox("Timeframe", ['1W', '1M', 'YTD', '1Y', 'All'], index=2)
    
    if len(transactions_df) > 1:
        hist_df = calculate_historical_portfolio_value(transactions_df, datetime.now() - timedelta(days=730))
        chart = create_performance_chart(hist_df, tf)
        if chart: st.plotly_chart(chart, use_container_width=True)
        else: st.info("Not enough data for chart yet.")
    else:
        st.info("Add more transactions to see history.")

    # Allocation
    st.subheader("Allocation")
    c1, c2 = st.columns(2)
    h_chart, s_chart = create_allocation_charts(portfolio, cash)
    if h_chart: c1.plotly_chart(h_chart, use_container_width=True)
    if s_chart: c2.plotly_chart(s_chart, use_container_width=True)


def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        
    if not st.session_state['logged_in']:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
