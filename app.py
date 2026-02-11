import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from manager import PortfolioManager

# --- IMPORT LOGIC FROM YOUR ORIGINAL FILE ---
# Ensure portfolio_logic.py exists in your folder!
from portfolio_logic import (
    calculate_cash_balance,
    get_current_holdings,
    fetch_live_prices,
    build_portfolio_table,
    calculate_portfolio_metrics,
    calculate_historical_portfolio_value,
    get_sector_allocation
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Pro Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (From your original code) ---
st.markdown("""
    <style>
    .main { padding: 0rem 1rem; }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label { font-weight: 600; color: #31333F; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; }
    h1 { color: #1f77b4; font-weight: 700; }
    h2 { color: #2c3e50; margin-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION & MANAGER ---
@st.cache_resource
def get_manager():
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        return PortfolioManager(creds_info)
    
    creds_path = 'credentials.json'
    if os.path.exists(creds_path):
        return PortfolioManager(creds_path)
    
    st.error("Missing Credentials! Please add them to Streamlit Secrets.")
    st.stop()

manager = get_manager()

# --- SESSION STATE SETUP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_tab' not in st.session_state:
    st.session_state.user_tab = None
# ADDED: Alerts Tab State
if 'alerts_tab' not in st.session_state:
    st.session_state.alerts_tab = None

# --- HELPER FUNCTIONS FOR USER TAB ---
def load_user_transactions():
    """Load transactions from the user's specific tab."""
    try:
        data = st.session_state.user_tab.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty and 'Type' in df.columns:
             # Basic type conversion
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def add_user_transaction(date, ticker, trans_type, quantity, price):
    """Append a row to the user's tab."""
    try:
        st.session_state.user_tab.append_row([
            date.strftime('%Y-%m-%d'),
            ticker,
            trans_type,
            quantity,
            price
        ])
        st.cache_data.clear() # Clear cache to refresh UI
        return True
    except Exception as e:
        st.error(f"Failed to add transaction: {e}")
        return False

# --- ADDED: ALERTS HELPER FUNCTIONS ---
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
            st.cache_data.clear()
            return True
        else:
            st.error("Alerts tab not found.")
            return False
    except Exception as e:
        st.error(f"Error adding alert: {e}")
        return False

# --- CHARTING FUNCTIONS ---
def create_performance_chart(historical_df, timeframe):
    # This is EXACTLY your original function
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
                             mode='lines', name='Your Portfolio', line=dict(color='#1f77b4', width=3)))
    fig.add_trace(go.Scatter(x=filtered['Date'], y=filtered['SPY_Return_%'], 
                             mode='lines', name='S&P 500', line=dict(color='#ff7f0e', width=2, dash='dash')))
    fig.update_layout(title='Performance vs S&P 500', template='plotly_white', height=400, hovermode='x unified')
    return fig

def create_allocation_charts(portfolio_df, cash_balance):
    if portfolio_df.empty: return None, None
    
    # --- 1. Holdings Chart (Left Side) ---
    # הכנת הנתונים: מניות + מזומן
    holdings = portfolio_df[['Ticker', 'Market Value']].copy()
    holdings_with_cash = pd.concat([holdings, pd.DataFrame([{'Ticker': 'Cash', 'Market Value': cash_balance}])])
    
    # יצירת הגרף בסגנון "דונאט"
    fig1 = px.pie(
        holdings_with_cash, 
        values='Market Value', 
        names='Ticker', 
        title='Holdings Allocation', 
        hole=0.5, # חור באמצע (דונאט) למראה נקי יותר
        color_discrete_sequence=px.colors.qualitative.Pastel # צבעים נעימים יותר
    )
    
    # עיצוב הטקסט בתוך הגרף: רק אחוזים, כדי לחסוך מקום
    fig1.update_traces(textposition='inside', textinfo='percent')
    
    # עיצוב כללי: שוליים צמודים ומקרא למטה
    fig1.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",       # מקרא אופקי
            yanchor="bottom", y=-0.2, # ממוקם מתחת לגרף
            xanchor="center", x=0.5
        ),
        margin=dict(l=20, r=20, t=40, b=20), # שוליים מינימליים
        height=350 # גובה קבוע שמונע מתיחה
    )
    
    # --- 2. Sector Chart (Right Side) ---
    sector_data = get_sector_allocation(portfolio_df)
    fig2 = None
    if not sector_data.empty:
        fig2 = px.pie(
            sector_data, 
            values='Value', 
            names='Sector', 
            title='Sector Allocation', 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig2.update_traces(textposition='inside', textinfo='percent')
        
        # אותו עיצוב בדיוק כדי שיהיה סימטרי
        fig2.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom", y=-0.2,
                xanchor="center", x=0.5
            ),
            margin=dict(l=20, r=20, t=40, b=20),
            height=350
        )
        
    return fig1, fig2
    
# ==========================================
#               MAIN APP LOGIC
# ==========================================

if not st.session_state.logged_in:
    # --- LOGIN SCREEN ---
    st.title("📈 Pro Portfolio Tracker")
    st.markdown("### Please Login to view your portfolio")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login", type="primary"):
            # UPDATED: Unpacking 3 values now
            success, user_tab, alerts_tab = manager.login(u, p)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_tab = user_tab
                st.session_state.alerts_tab = alerts_tab # Saving alerts tab
                st.success(f"Welcome back, {u}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
                
    with tab2:
        new_u = st.text_input("Choose Username", key="reg_u")
        new_p = st.text_input("Choose Password", type="password", key="reg_p")
        email = st.text_input("Email", key="reg_e")
        if st.button("Create Account"):
            success, msg = manager.sign_up(new_u, new_p, email)
            if success:
                st.success(msg)
            else:
                st.error(msg)

else:
    # --- LOGGED IN DASHBOARD ---
    
    # Sidebar
    st.sidebar.title(f"👤 {st.session_state.user_tab.title}")
    if st.sidebar.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.user_tab = None
        st.session_state.alerts_tab = None
        st.rerun()
        
    st.sidebar.header("📝 Transaction Management")
    
    with st.sidebar.expander("➕ Add Transaction", expanded=True):
        t_type = st.selectbox("Type", ['Buy', 'Sell', 'Deposit', 'Withdraw'])
        t_date = st.date_input("Date", value=datetime.now())
        
        if t_type in ['Buy', 'Sell']:
            t_ticker = st.text_input("Ticker", "").upper()
            t_qty = st.number_input("Quantity", min_value=0.0, step=0.01)
            t_price = st.number_input("Price ($)", min_value=0.0, step=0.01)
        else:
            t_ticker = 'CASH'
            t_qty = 1.0
            t_price = st.number_input("Amount ($)", min_value=0.0, step=0.01)
            
        if st.sidebar.button("Add Transaction", type="primary"):
            if add_user_transaction(t_date, t_ticker, t_type, t_qty, t_price):
                st.success("Transaction Added!")
                st.rerun()

    # --- ADDED: ALERTS SIDEBAR ---
    with st.sidebar.expander("🔔 Set Price Alert"):
        alert_ticker = st.text_input("Ticker for Alert").upper()
        alert_price = st.number_input("Target Price ($)", min_value=0.0)
        alert_cond = st.selectbox("Condition", ["Above", "Below"])
        
        if st.sidebar.button("Set Alert"):
            if add_alert_to_sheet(alert_ticker, alert_price, alert_cond):
                st.success(f"Alert set for {alert_ticker}!")
                st.rerun()
    # -----------------------------

    # Main Content
    st.title("📈 Pro Portfolio Tracker")
    st.markdown("*Real-time analytics for your personal portfolio*")

    # Load Data
    transactions_df = load_user_transactions()
    
    if transactions_df.empty:
        st.info("👋 Welcome! Your portfolio is empty. Add your first transaction in the sidebar.")
        st.stop()
        
    # Calculate Logic
    cash_balance = calculate_cash_balance(transactions_df)
    holdings_df = get_current_holdings(transactions_df)
    
    if holdings_df.empty:
         st.info(f"💰 Cash Balance: ${cash_balance:,.2f}. Start investing!")
         st.stop()
         
    # Fetch Prices & Build Tables
    with st.spinner("Fetching market data..."):
        tickers = holdings_df['Ticker'].unique().tolist()
        price_data = fetch_live_prices(tickers)
        
    portfolio_df = build_portfolio_table(holdings_df, price_data, cash_balance)
    metrics = calculate_portfolio_metrics(portfolio_df, cash_balance, transactions_df)
    
    # --- METRICS DISPLAY ---
    st.markdown("## 📊 Portfolio Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${metrics['total_portfolio_value']:,.2f}")
    c2.metric("Cash", f"${metrics['cash_balance']:,.2f}")
    c3.metric("Total Return", f"${metrics['total_return_dollars']:,.2f}", f"{metrics['total_return_pct']:.2f}%")
    c4.metric("Daily P&L", f"${metrics['daily_pnl']:,.2f}")
    
    # --- HOLDINGS TABLE ---
    st.markdown("## 💼 Holdings")
    st.dataframe(portfolio_df.style.format({"Market Value": "${:,.2f}", "Current Price": "${:,.2f}"}), use_container_width=True)
    
    # --- CHARTS (RESTORED ORIGINAL LAYOUT) ---
    st.markdown("## 📈 Performance & Allocation")
    
    # Historical Chart
    timeframe = st.selectbox("Timeframe", ['1W', '1M', 'YTD', '1Y', 'All'], index=2)
    
    if timeframe == 'All': start = transactions_df['Date'].min()
    elif timeframe == 'YTD': start = datetime(datetime.now().year, 1, 1)
    elif timeframe == '1Y': start = datetime.now() - timedelta(days=365)
    elif timeframe == '1M': start = datetime.now() - timedelta(days=30)
    else: start = datetime.now() - timedelta(days=7) # 1W
    
    hist_df = calculate_historical_portfolio_value(transactions_df, start)
    if not hist_df.empty:
        st.plotly_chart(create_performance_chart(hist_df, timeframe), use_container_width=True)
        
    # Pie Charts
    c1, c2 = st.columns(2)
    fig_holdings, fig_sector = create_allocation_charts(portfolio_df, cash_balance)
    if fig_holdings: c1.plotly_chart(fig_holdings, use_container_width=True)
    if fig_sector: c2.plotly_chart(fig_sector, use_container_width=True)

    # --- ADDED: ACTIVE ALERTS SECTION ---
    st.markdown("## 🔔 Active Alerts")
    alerts_df = load_alerts()
    if not alerts_df.empty:
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active alerts configured.")

    # Footer
    st.markdown("---")
    st.markdown("*Data updated in real-time • Powered by yfinance & Google Sheets*")
