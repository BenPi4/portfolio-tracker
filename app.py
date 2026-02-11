"""
Pro Portfolio Tracker - Secure Multi-User Edition (ID Based)
Uses Sheet IDs for maximum privacy and separation.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import time

# Import calculation logic
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
def get_google_sheets_client():
    """Initialize Google Sheets client."""
    try:
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets['gcp_service_account'])
        else:
            credentials_json = os.getenv('GOOGLE_CREDENTIALS')
            if credentials_json:
                credentials_dict = json.loads(credentials_json)
            else:
                st.error("Google Sheets credentials not found!")
                return None
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def check_login(client, main_sheet_name, username, password):
    """Verify credentials and return the unique SHEET ID."""
    try:
        # We open the main ADMIN sheet by name (only the admin needs to know this name)
        # Note: If you renamed your main sheet, update the name in .env or secrets
        sh = client.open(main_sheet_name)
        worksheet = sh.worksheet('Users')
        users_data = worksheet.get_all_records()
        
        for user in users_data:
            if str(user['Username']).lower() == username.lower() and str(user['Password']) == password:
                # Return the ID, not the name
                return user['Sheet_ID']
        
        return None
    except Exception as e:
        st.error(f"Login System Error: Could not access user database. ({e})")
        return None

def login_page():
    """Display the login screen."""
    st.markdown("<h1 style='text-align: center;'>🔐 Secure Portfolio Login</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                client = get_google_sheets_client()
                main_sheet = os.getenv('GOOGLE_SHEET_NAME', 'Portfolio Tracker')
                
                if client:
                    with st.spinner("Verifying credentials..."):
                        # This returns the ID now
                        target_sheet_id = check_login(client, main_sheet, username, password)
                        
                        if target_sheet_id:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.session_state['sheet_id'] = target_sheet_id # Store ID
                            st.success(f"Welcome back, {username}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Incorrect username or password")

# --- Data Loading Functions (Updated to use ID) ---

@st.cache_data(ttl=60)
def load_transactions(_client, sheet_id):
    """Load transactions using Sheet ID (Secure)."""
    try:
        # open_by_key is the safest way to open a specific sheet
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Transactions')
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Access Denied or Sheet Not Found. Please ensure you shared the sheet with the Service Account email. (Error: {e})")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_alerts(_client, sheet_id):
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Alerts')
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Target_Price'] = pd.to_numeric(df['Target_Price'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

def add_transaction(client, sheet_id, transaction_data):
    try:
        spreadsheet = client.open_by_key(sheet_id)
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

def add_alert(client, sheet_id, alert_data):
    try:
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet('Alerts')
        worksheet.append_row([
            alert_data['Ticker'],
            alert_data['Target_Price'],
            alert_data['Condition'],
            'False'
        ])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- Chart Functions (Reused) ---
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

    client = get_google_sheets_client()
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
            if add_transaction(client, sheet_id, data):
                st.success("Added!")
                time.sleep(0.5)
                st.rerun()

    # Load Data
    with st.spinner("Loading your personal data..."):
        transactions_df = load_transactions(client, sheet_id)
    
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
