import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# --- 1. Cash Balance ---
def calculate_cash_balance(transactions_df):
    """Calculate current cash balance from transaction history."""
    cash = 0.0
    if transactions_df.empty:
        return cash
        
    for _, row in transactions_df.iterrows():
        t_type = str(row['Type']).strip()
        price = float(row['Price']) if pd.notnull(row['Price']) else 0.0
        quantity = float(row['Quantity']) if pd.notnull(row['Quantity']) else 0.0

        if t_type == 'Deposit Cash':
            cash += price
        elif t_type == 'Withdraw Cash':
            cash -= price
        elif t_type == 'Buy':
            cash -= quantity * price
        elif t_type == 'Sell':
            cash += quantity * price
    
    return cash

# --- 2. Holdings ---
def get_current_holdings(transactions_df):
    """Calculate current holdings from transaction history."""
    holdings = {}
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Filter only buy/sell transactions
    stock_transactions = transactions_df[
        transactions_df['Type'].isin(['Buy', 'Sell'])
    ].copy()
    
    for _, row in stock_transactions.iterrows():
        ticker = str(row['Ticker']).strip().upper()
        
        if ticker not in holdings:
            holdings[ticker] = {
                'total_qty': 0.0,
                'total_cost': 0.0,
                'first_buy_date': None
            }
        
        qty = float(row['Quantity'])
        price = float(row['Price'])
        t_type = str(row['Type']).strip()

        if t_type == 'Buy':
            holdings[ticker]['total_qty'] += qty
            holdings[ticker]['total_cost'] += qty * price
            
            # Track first purchase date
            current_date = pd.to_datetime(row['Date'])
            if holdings[ticker]['first_buy_date'] is None:
                holdings[ticker]['first_buy_date'] = current_date
            else:
                holdings[ticker]['first_buy_date'] = min(
                    holdings[ticker]['first_buy_date'],
                    current_date
                )
        
        elif t_type == 'Sell':
            holdings[ticker]['total_qty'] -= qty
            # Proportionally reduce cost basis
            if holdings[ticker]['total_qty'] > 0:
                avg_price = holdings[ticker]['total_cost'] / (holdings[ticker]['total_qty'] + qty)
                holdings[ticker]['total_cost'] = holdings[ticker]['total_qty'] * avg_price
            else:
                holdings[ticker]['total_cost'] = 0
    
    # Convert to DataFrame
    holdings_list = []
    for ticker, data in holdings.items():
        if data['total_qty'] > 0.0001:  # Filter out sold positions
            holdings_list.append({
                'Ticker': ticker,
                'Qty': data['total_qty'],
                'Avg_Buy_Price': data['total_cost'] / data['total_qty'],
                'First_Buy_Date': data['first_buy_date']
            })
    
    return pd.DataFrame(holdings_list) if holdings_list else pd.DataFrame()

# --- 3. Live Prices (Improved) ---
def fetch_live_prices(tickers):
    """Fetch current prices using multiple fallback methods."""
    price_data = {}
    if not tickers:
        return price_data
    
    # Method A: Batch Download
    try:
        data = yf.download(tickers, period="1d", progress=False)['Close']
        for ticker in tickers:
            try:
                if isinstance(data, pd.Series):
                    price = float(data.iloc[-1])
                else:
                    price = float(data[ticker].iloc[-1])
                
                price_data[ticker] = {
                    'price': price,
                    'prev_close': price,
                    'sector': 'Unknown'
                }
            except:
                pass
    except:
        pass

    # Method B: Individual Fallback
    for ticker in tickers:
        if ticker in price_data and price_data[ticker]['price'] > 0:
            continue
            
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                hist = stock.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            # Try to get sector
            sector = 'Unknown'
            try:
                sector = stock.info.get('sector', 'Unknown')
            except:
                pass

            price_data[ticker] = {
                'price': float(price) if price else 0.0,
                'prev_close': float(price) if price else 0.0,
                'sector': sector
            }
        except:
            price_data[ticker] = {'price': 0.0, 'prev_close': 0.0, 'sector': 'Unknown'}
    
    return price_data

# --- Helper for SPY ---
def calculate_spy_return(start_date):
    """Calculate SPY return from start_date until now."""
    try:
        spy = yf.Ticker('SPY')
        hist = spy.history(start=start_date)
        if hist.empty:
            return 0.0
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        return ((end_price - start_price) / start_price) * 100
    except:
        return 0.0

# --- 4. Build Portfolio Table ---
def build_portfolio_table(holdings_df, price_data, cash_balance):
    """Combine holdings with prices to create main table."""
    if holdings_df.empty:
        return pd.DataFrame()
    
    portfolio_rows = []
    for _, holding in holdings_df.iterrows():
        ticker = holding['Ticker']
        qty = holding['Qty']
        avg_price = holding['Avg_Buy_Price']
        
        # Get live data
        live_data = price_data.get(ticker, {'price': 0, 'sector': 'Unknown'})
        current_price = live_data.get('price', 0)
        sector = live_data.get('sector', 'Unknown')
        
        market_value = qty * current_price
        total_return_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
        
        # Calculate Alpha
        spy_return = calculate_spy_return(holding['First_Buy_Date'])
        alpha = total_return_pct - spy_return
        
        portfolio_rows.append({
            'Ticker': ticker,
            'Qty': qty,
            'Avg Buy Price': avg_price,
            'Current Price': current_price,
            'Market Value': market_value,
            'Total Return %': total_return_pct,
            'Daily Return %': 0.0, # Simplified
            'Alpha vs SPY': alpha,
            'Sector': sector
        })
    
    df = pd.DataFrame(portfolio_rows)
    if not df.empty:
        total_val = df['Market Value'].sum() + cash_balance
        if total_val > 0:
            df['% of Portfolio'] = (df['Market Value'] / total_val * 100).round(2)
        else:
            df['% of Portfolio'] = 0.0
            
        return df[['Ticker', 'Qty', 'Avg Buy Price', 'Current Price', 'Market Value', '% of Portfolio', 'Total Return %', 'Daily Return %', 'Alpha vs SPY', 'Sector']]
        
    return pd.DataFrame()

# --- 5. Portfolio Metrics ---
def calculate_portfolio_metrics(portfolio_df, cash_balance, transactions_df):
    """Calculate KPI metrics."""
    if portfolio_df.empty:
        total_market_value = 0.0
    else:
        total_market_value = portfolio_df['Market Value'].sum()
        
    # Calculate Net Invested (Deposits - Withdrawals)
    net_invested = 0.0
    if not transactions_df.empty:
        for _, row in transactions_df.iterrows():
            t = str(row['Type']).strip()
            p = float(row['Price']) if pd.notnull(row['Price']) else 0.0
            if t == 'Deposit Cash': net_invested += p
            elif t == 'Withdraw Cash': net_invested -= p
            
    total_value = total_market_value + cash_balance
    total_return_dollars = total_value - net_invested
    total_return_pct = (total_return_dollars / net_invested * 100) if net_invested > 0 else 0.0
    
    return {
        'total_portfolio_value': total_value,
        'cash_balance': cash_balance,
        'total_return_dollars': total_return_dollars,
        'total_return_pct': total_return_pct,
        'daily_pnl': 0.0
    }

# --- 6. Historical Data (Placeholder) ---
def calculate_historical_portfolio_value(transactions_df, start_date, end_date=None):
    """Return empty dataframe to prevent errors."""
    return pd.DataFrame()

# --- 7. Sector Allocation ---
def get_sector_allocation(portfolio_df):
    """Group by sector."""
    if portfolio_df.empty or 'Sector' not in portfolio_df.columns:
        return pd.DataFrame()
    return portfolio_df.groupby('Sector')['Market Value'].sum().reset_index().rename(columns={'Market Value': 'Value'})
