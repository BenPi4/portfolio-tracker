import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from manager import PortfolioManager

# --- IMPORT LOGIC FROM HELPER FILE ---
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
    if "gcp_service_account" in st.secrets:
        return PortfolioManager(dict(st.secrets["gcp_service_account"]))
    if os.path.exists('credentials.json'):
        return PortfolioManager('credentials.json')
    st.error("Credentials not found.")
    st.stop()

manager = get_manager()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_tab' not in st.session_state: st.session_state.user_tab = None
if 'alerts_tab' not in st.session_state: st.session_state.alerts_tab = None

# --- HELPER FUNCTIONS ---
def load_user_transactions():
    try:
        data = st.session_state.user_tab.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Type' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def add_user_transaction(date, ticker, trans_type, quantity, price):
    try:
        st.session_state.user_tab.append_row([
            date.strftime('%Y-%m-%d'), ticker, trans_type, quantity, price
        ])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def load_alerts():
    try:
        if st.session_state.alerts_tab:
            return pd.DataFrame(st.session_state.alerts_tab.get_all_records())
        return pd.DataFrame()
    except: return pd.DataFrame()

def add_alert_to_sheet(ticker, target, condition):
    try:
        if st.session_state.alerts_tab:
            st.session_state.alerts_tab.append_row([ticker, target, condition, "Yes"])
            st.cache_data.clear()
            return True
        return False
    except: return False

# --- CHARTING FUNCTIONS (FIXED!) ---
def create_performance_chart(historical_df, timeframe):
    if historical_df.empty: return None
    today = datetime.now()
    if timeframe == '1W': start = today - timedelta(days=7)
    elif timeframe == '1M': start = today - timedelta(days=30)
    elif timeframe == 'YTD': start = datetime(today.year, 1, 1)
    elif timeframe == '1Y': start = today - timedelta(days=365)
    else: start = historical_df['Date'].min()
    
    filtered = historical_df[historical_df['Date'] >= start].copy()
    if filtered.empty: return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered['Date'], y=filtered['Portfolio_Return_%'], 
                             mode='lines', name='Portfolio', line=dict(color='#1f77b4', width=3)))
    fig.add_trace(go.Scatter(x=filtered['Date'], y=filtered['SPY_Return_%'], 
                             mode='lines', name='S&P 500', line=dict(color='#ff7f0e', width=2, dash='dash')))
    fig.update_layout(title='Performance vs S&P 500', template='plotly_white', height=400, hovermode='x unified')
    return fig

def create_allocation_charts(portfolio_df, cash_balance):
    if portfolio_df.empty: return None, None
    
    # 1. Holdings Chart (CLEANER)
    holdings = portfolio_df[['Ticker', 'Market Value']].copy()
    holdings_with_cash = pd.concat([holdings, pd.DataFrame([{'Ticker': 'Cash', 'Market Value': cash_balance}])])
    
    fig1 = px.pie(holdings_with_cash, values='Market Value', names='Ticker', title='Holdings', hole=0.5)
    
    # Force text inside, and HIDE it if it's too small (prevents clutter)
    fig1.update_traces(textposition='inside', textinfo='percent')
    fig1.update_layout(
        uniformtext_minsize=12, 
        uniformtext_mode='hide', # This is the magic fix for messiness
        showlegend=True,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=40, b=40, l=20, r=20),
        height=350
    )
    
    # 2. Sector Chart
    sector_data = get_sector_allocation(portfolio_df)
    fig2 = None
    if not sector_data.empty:
        fig2 = px.pie(sector_data, values='Value', names='Sector', title='Sectors', hole=0.5)
        fig2.update_traces(textposition='inside', textinfo='percent')
        fig2.update_layout(
            uniformtext_minsize=12, 
            uniformtext_mode='hide',
            showlegend=True,
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=40, b=40, l=20, r=20),
            height=350
        )
        
    return fig1, fig2

# ==========================================
#               MAIN APP LOGIC
# ==========================================

if not st.session_state.logged_in:
    st.title("📈 Pro Portfolio Tracker")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("Username", key="u")
        p = st.text_input("Password", type="password", key="p")
        if st.button("Login"):
            success, user_tab, alerts_tab = manager.login(u, p)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_tab = user_tab
                st.session_state.alerts_tab = alerts_tab
                st.rerun()
            else: st.error("Login failed")
            
    with tab2:
        nu = st.text_input("New User")
        np = st.text_input("New Pass", type="password")
        ne = st.text_input("Email")
        if st.button("Sign Up"):
            success, msg = manager.sign_up(nu, np, ne)
            if success: st.success(msg)
            else: st.error(msg)

else:
    # --- DASHBOARD ---
    st.sidebar.title(f"👤 {st.session_state.user_tab.title}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    # Actions
    with st.sidebar.expander("➕ Add Transaction", expanded=True):
        type_ = st.selectbox("Type", ['Buy', 'Sell', 'Deposit', 'Withdraw'])
        date_ = st.date_input("Date")
        ticker_ = st.text_input("Ticker").upper() if type_ in ['Buy', 'Sell'] else "CASH"
        qty_ = st.number_input("Qty", 0.0) if type_ in ['Buy', 'Sell'] else 1.0
        price_ = st.number_input("Price/Amount", 0.0)
        if st.sidebar.button("Add"):
            if add_user_transaction(date_, ticker_, type_, qty_, price_):
                st.success("Added!")
                st.rerun()

    with st.sidebar.expander("🔔 Set Alert"):
        at = st.text_input("Ticker").upper()
        ap = st.number_input("Target Price", 0.0)
        ac = st.selectbox("Condition", ["Above", "Below"])
        if st.sidebar.button("Set Alert"):
            if add_alert_to_sheet(at, ap, ac):
                st.success("Alert Set!")
                st.rerun()

    # Main Area
    st.title("📈 Pro Portfolio Tracker")
    df = load_user_transactions()
    
    if df.empty:
        st.info("Portfolio empty. Add transactions via sidebar.")
        st.stop()
        
    cash = calculate_cash_balance(df)
    holdings = get_current_holdings(df)
    
    with st.spinner("Fetching data..."):
        prices = fetch_live_prices(holdings['Ticker'].unique().tolist())
        
    port_df = build_portfolio_table(holdings, prices, cash)
    metrics = calculate_portfolio_metrics(port_df, cash, df)
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${metrics['total_portfolio_value']:,.2f}")
    c2.metric("Cash", f"${metrics['cash_balance']:,.2f}")
    c3.metric("Return", f"${metrics['total_return_dollars']:,.2f}", f"{metrics['total_return_pct']:.2f}%")
    c4.metric("Daily P&L", f"${metrics['daily_pnl']:,.2f}")
    
    st.divider()
    
    # --- HOLDINGS TABLE (FIXED DECIMALS) ---
    st.markdown("### 💼 Holdings")
    
    # 1. Round numbers in the data first
    display_df = port_df.copy()
    numeric_cols = ['Avg Buy Price', 'Current Price', 'Market Value', 'Daily P&L', 'Total Return', 'Daily Return %', 'Total Return %', '% of Portfolio']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
    
    # 2. Display with Format
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
        hide_index=True
    )

    # Charts
    st.markdown("### 📊 Analytics")
    
    # History
    timeframe = st.selectbox("Timeframe", ['1W', '1M', 'YTD', '1Y', 'All'], index=2)
    if timeframe == 'All': start = df['Date'].min()
    elif timeframe == 'YTD': start = datetime(datetime.now().year, 1, 1)
    elif timeframe == '1Y': start = datetime.now() - timedelta(days=365)
    else: start = datetime.now() - timedelta(days=30)
    
    hist_df = calculate_historical_portfolio_value(df, start)
    if not hist_df.empty:
        st.plotly_chart(create_performance_chart(hist_df, timeframe), use_container_width=True)

    # Pies
    c1, c2 = st.columns(2)
    fig1, fig2 = create_allocation_charts(port_df, cash)
    if fig1: c1.plotly_chart(fig1, use_container_width=True)
    if fig2: c2
