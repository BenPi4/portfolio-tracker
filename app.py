"""
Pro Portfolio Tracker - Main Streamlit Application
A comprehensive portfolio management dashboard with real-time data.
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

# Import our calculation logic
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


# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        font-weight: 600;
        color: #31333F;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }
    h1 {
        color: #1f77b4;
        font-weight: 700;
    }
    h2 {
        color: #2c3e50;
        margin-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_google_sheets_client():
    """
    Initialize and return Google Sheets client.
    Uses service account credentials from Streamlit secrets or environment.
    """
    try:
        # Try to get credentials from Streamlit secrets first
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets['gcp_service_account'])
        else:
            # Fallback to environment variable
            credentials_json = os.getenv('GOOGLE_CREDENTIALS')
            if credentials_json:
                credentials_dict = json.loads(credentials_json)
            else:
                st.error("Google Sheets credentials not found!")
                return None
        
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict, scope
        )
        client = gspread.authorize(credentials)
        
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_transactions(_client, sheet_name):
    """Load transactions from Google Sheet."""
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet('Transactions')
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure proper data types
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_alerts(_client, sheet_name):
    """Load alerts from Google Sheet."""
    try:
        spreadsheet = _client.open(sheet_name)
        worksheet = spreadsheet.worksheet('Alerts')
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['Target_Price'] = pd.to_numeric(df['Target_Price'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading alerts: {e}")
        return pd.DataFrame()


def add_transaction(client, sheet_name, transaction_data):
    """Add a new transaction to Google Sheet."""
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet('Transactions')
        
        # Append row
        worksheet.append_row([
            transaction_data['Date'].strftime('%Y-%m-%d'),
            transaction_data['Ticker'],
            transaction_data['Type'],
            transaction_data['Quantity'],
            transaction_data['Price']
        ])
        
        # Clear cache to reload data
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error adding transaction: {e}")
        return False


def add_alert(client, sheet_name, alert_data):
    """Add a new price alert to Google Sheet."""
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet('Alerts')
        
        # Append row
        worksheet.append_row([
            alert_data['Ticker'],
            alert_data['Target_Price'],
            alert_data['Condition'],
            'False'  # Email_Sent
        ])
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error adding alert: {e}")
        return False


def create_performance_chart(historical_df, timeframe):
    """Create historical performance comparison chart."""
    if historical_df.empty:
        return None
    
    # Filter by timeframe
    today = datetime.now()
    if timeframe == '1W':
        start_date = today - timedelta(days=7)
    elif timeframe == '1M':
        start_date = today - timedelta(days=30)
    elif timeframe == 'YTD':
        start_date = datetime(today.year, 1, 1)
    elif timeframe == '1Y':
        start_date = today - timedelta(days=365)
    else:  # All
        start_date = historical_df['Date'].min()
    
    filtered_df = historical_df[historical_df['Date'] >= start_date].copy()
    
    if filtered_df.empty:
        return None
    
    fig = go.Figure()
    
    # Portfolio line
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Portfolio_Return_%'],
        mode='lines',
        name='Your Portfolio',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    
    # SPY line
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['SPY_Return_%'],
        mode='lines',
        name='S&P 500 (SPY)',
        line=dict(color='#ff7f0e', width=2, dash='dash'),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='Portfolio Performance vs S&P 500',
        xaxis_title='Date',
        yaxis_title='Cumulative Return (%)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_allocation_charts(portfolio_df, cash_balance):
    """Create holdings and sector allocation pie charts with better layout."""
    if portfolio_df.empty:
        return None, None
    
    # --- 1. Holdings Chart ---
    holdings_data = portfolio_df[['Ticker', 'Market Value']].copy()
    
    # Add cash row
    if cash_balance > 0:
        cash_row = pd.DataFrame([{'Ticker': 'CASH', 'Market Value': cash_balance}])
        holdings_with_cash = pd.concat([holdings_data, cash_row])
    else:
        holdings_with_cash = holdings_data
    
    # Create Chart
    fig_holdings = px.pie(
        holdings_with_cash,
        values='Market Value',
        names='Ticker',
        title='Holdings Allocation',
        hole=0.4, # Donut style
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Clean Layout
    fig_holdings.update_traces(
        textposition='inside', # Force text inside slices
        textinfo='percent+label'
    )
    fig_holdings.update_layout(
        margin=dict(l=20, r=20, t=40, b=20), # Add margins
        height=400,
        legend=dict(
            orientation="h",       # Horizontal legend
            yanchor="bottom",
            y=-0.2,                # Move below chart
            xanchor="center",
            x=0.5
        )
    )
    
    # --- 2. Sector Chart ---
    sector_data = get_sector_allocation(portfolio_df)
    
    if not sector_data.empty:
        fig_sector = px.pie(
            sector_data,
            values='Value',
            names='Sector',
            title='Sector Allocation',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_sector.update_traces(
            textposition='inside',
            textinfo='percent+label'
        )
        fig_sector.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
    else:
        fig_sector = None
    
    return fig_holdings, fig_sector


def main():
    """Main application logic."""
    
    # Title
    st.title("📈 Pro Portfolio Tracker")
    st.markdown("*Real-time portfolio management & analytics*")
    
    # Get Google Sheets client
    client = get_google_sheets_client()
    
    if client is None:
        st.warning("⚠️ Please configure Google Sheets credentials to continue.")
        st.info("""
        **Setup Instructions:**
        1. Create a Google Cloud project and enable Google Sheets API
        2. Create a service account and download credentials JSON
        3. Add credentials to Streamlit secrets or environment variable
        4. Share your Google Sheet with the service account email
        """)
        return
    
    # Get sheet name from config
    sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Portfolio Tracker')
    
    # Sidebar - Transaction Management
    st.sidebar.header("📝 Transaction Management")
    
    with st.sidebar.expander("➕ Add Transaction", expanded=True):
        transaction_type = st.selectbox(
            "Type",
            ['Buy', 'Sell', 'Deposit Cash', 'Withdraw Cash']
        )
        
        transaction_date = st.date_input(
            "Date",
            value=datetime.now()
        )
        
        if transaction_type in ['Buy', 'Sell']:
            ticker = st.text_input("Ticker (e.g., AAPL)", "").upper()
            quantity = st.number_input("Quantity", min_value=0.0, step=0.01, value=1.0)
            price = st.number_input("Price ($)", min_value=0.0, step=0.01, value=100.0)
        else:
            ticker = 'CASH'
            quantity = 1.0
            price = st.number_input("Amount ($)", min_value=0.0, step=0.01, value=1000.0)
        
        if st.button("Add Transaction", type="primary"):
            if transaction_type in ['Buy', 'Sell'] and not ticker:
                st.error("Please enter a ticker symbol")
            else:
                transaction_data = {
                    'Date': transaction_date,
                    'Ticker': ticker,
                    'Type': transaction_type,
                    'Quantity': quantity,
                    'Price': price
                }
                
                if add_transaction(client, sheet_name, transaction_data):
                    st.success(f"✅ {transaction_type} transaction added!")
                    st.rerun()
    
    with st.sidebar.expander("🔔 Set Price Alert"):
        alert_ticker = st.text_input("Alert Ticker", "").upper()
        target_price = st.number_input("Target Price ($)", min_value=0.0, step=0.01, value=100.0)
        condition = st.selectbox("Condition", ['Above', 'Below'])
        
        if st.button("Create Alert"):
            if not alert_ticker:
                st.error("Please enter a ticker symbol")
            else:
                alert_data = {
                    'Ticker': alert_ticker,
                    'Target_Price': target_price,
                    'Condition': condition
                }
                
                if add_alert(client, sheet_name, alert_data):
                    st.success("✅ Alert created!")
                    st.rerun()
    
    # Load data
    with st.spinner("Loading portfolio data..."):
        transactions_df = load_transactions(client, sheet_name)
    
    if transactions_df.empty:
        st.info("📊 No transactions found. Add your first transaction to get started!")
        return
    
    # Calculate portfolio data
    cash_balance = calculate_cash_balance(transactions_df)
    holdings_df = get_current_holdings(transactions_df)
    
    if holdings_df.empty:
        st.info("💰 You have ${:.2f} in cash. Start investing!".format(cash_balance))
        return
    
    # Fetch live prices
    tickers = holdings_df['Ticker'].unique().tolist()
    
    with st.spinner("Fetching live market data..."):
        price_data = fetch_live_prices(tickers)
    
    # Build portfolio table
    portfolio_df = build_portfolio_table(holdings_df, price_data, cash_balance)
    metrics = calculate_portfolio_metrics(portfolio_df, cash_balance, transactions_df)
    
    # Top Metrics (KPIs)
    st.markdown("## 📊 Portfolio Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Portfolio Value",
            f"${metrics['total_portfolio_value']:,.2f}"
        )
    
    with col2:
        st.metric(
            "Cash Balance",
            f"${metrics['cash_balance']:,.2f}"
        )
    
    with col3:
        delta_color = "normal" if metrics['total_return_dollars'] >= 0 else "inverse"
        st.metric(
            "Total Return",
            f"${metrics['total_return_dollars']:,.2f}",
            f"{metrics['total_return_pct']:.2f}%",
            delta_color=delta_color
        )
    
    with col4:
        delta_color = "normal" if metrics['daily_pnl'] >= 0 else "inverse"
        st.metric(
            "Daily P&L",
            f"${metrics['daily_pnl']:,.2f}",
            delta_color=delta_color
        )
    
    # Main Portfolio Table
    st.markdown("## 💼 Holdings")
    
    # Format the dataframe for display
    display_df = portfolio_df.copy()
    
    # Format currency columns
    currency_cols = ['Avg Buy Price', 'Current Price', 'Market Value']
    for col in currency_cols:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
    
    # Format percentage columns
    pct_cols = ['% of Portfolio', 'Total Return %', 'Daily Return %', 'Alpha vs SPY']
    for col in pct_cols:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")
    
    # Display with highlighting
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Historical Performance Chart
    st.markdown("## 📈 Historical Performance")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        timeframe = st.selectbox(
            "Timeframe",
            ['1W', '1M', 'YTD', '1Y', 'All'],
            index=2
        )
    
    # Calculate historical data
    if timeframe == 'All':
        start_date = transactions_df['Date'].min()
    elif timeframe == 'YTD':
        start_date = datetime(datetime.now().year, 1, 1)
    elif timeframe == '1Y':
        start_date = datetime.now() - timedelta(days=365)
    elif timeframe == '1M':
        start_date = datetime.now() - timedelta(days=30)
    else:  # 1W
        start_date = datetime.now() - timedelta(days=7)
    
    with st.spinner("Calculating historical performance..."):
        historical_df = calculate_historical_portfolio_value(
            transactions_df,
            start_date
        )
    
    if not historical_df.empty:
        perf_chart = create_performance_chart(historical_df, timeframe)
        if perf_chart:
            st.plotly_chart(perf_chart, use_container_width=True)
    else:
        st.info("Not enough historical data to display chart")
    
    # Allocation Charts
    st.markdown("## 🥧 Portfolio Allocation")
    
    col1, col2 = st.columns(2)
    
    holdings_chart, sector_chart = create_allocation_charts(portfolio_df, cash_balance)
    
    with col1:
        if holdings_chart:
            st.plotly_chart(holdings_chart, use_container_width=True)
    
    with col2:
        if sector_chart:
            st.plotly_chart(sector_chart, use_container_width=True)
        else:
            st.info("Sector data not available")
    
    # Active Alerts
    st.markdown("## 🔔 Active Alerts")
    alerts_df = load_alerts(client, sheet_name)
    
    if not alerts_df.empty:
        active_alerts = alerts_df[alerts_df['Email_Sent'] == 'False']
        
        if not active_alerts.empty:
            st.dataframe(
                active_alerts[['Ticker', 'Target_Price', 'Condition']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No active alerts")
    else:
        st.info("No alerts configured")
    
    # Footer
    st.markdown("---")
    st.markdown("*Data updated in real-time • Powered by yfinance & Google Sheets*")


if __name__ == "__main__":
    main()
