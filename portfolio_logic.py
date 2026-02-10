import pandas as pd
import yfinance as yf
from datetime import datetime
import requests

# --- 1. Cash Balance ---
def calculate_cash_balance(transactions_df):
    cash = 0.0
    if transactions_df.empty:
        return cash
        
    for _, row in transactions_df.iterrows():
        t_type = str(row['Type']).strip()
        try:
            price = float(row['Price'])
            quantity = float(row['Quantity'])
        except:
            price = 0.0
            quantity = 0.0

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
    holdings = {}
    if transactions_df.empty:
        return pd.DataFrame()
    
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
            
            current_date = pd.to_datetime(row['Date'])
            if holdings[ticker]['first_buy_date'] is None:
                holdings[ticker]['first_buy_date'] = current_date
            else:
                if holdings[ticker]['first_buy_date'] is not None:
                    holdings[ticker]['first_buy_date'] = min(
                        holdings[ticker]['first_buy_date'],
                        current_date
                    )
        
        elif t_type == 'Sell':
            holdings[ticker]['total_qty'] -= qty
            if holdings[ticker]['total_qty'] > 0:
                avg_price = holdings[ticker]['total_cost'] / (holdings[ticker]['total_qty'] + qty)
                holdings[ticker]['total_cost'] = holdings[ticker]['total_qty'] * avg_price
            else:
                holdings[ticker]['total_cost'] = 0
    
    holdings_list = []
    for ticker, data in holdings.items():
        if data['total_qty'] > 0.0001:
            holdings_list.append({
                'Ticker': ticker,
                'Qty': data['total_qty'],
                'Avg_Buy_Price': data['total_cost'] / data['total_qty'],
                'First_Buy_Date': data['first_buy_date']
            })
    
    return pd.DataFrame(holdings_list) if holdings_list else pd.DataFrame()

# --- 3. Live Prices & Metadata (The Fix) ---
def fetch_live_prices(tickers):
    """Fetch price, previous close, and sector using robust methods."""
    price_data = {}
    if not tickers:
        return price_data
    
    # Session to mimic browser
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    for ticker in tickers:
        # Default values
        current_price = 0.0
        prev_close = 0.0
        sector = 'Unknown'
        
        try:
            stock = yf.Ticker(ticker, session=session)
            
            # A. Try fast_info first (Best for Price & Prev Close)
            try:
                current_price = stock.fast_info.last_price
                prev_close = stock.fast_info.previous_close
            except:
                pass
            
            # Fallback if fast_info fails
            if current_price == 0 or current_price is None:
                hist = stock.history(period='2d') # Get 2 days to find prev close
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    if len(hist) > 1:
                        prev_close = hist['Close'].iloc[-2]
                    else:
                        prev_close = current_price # Avoid division by zero
            
            # B. Try to get Sector (This is a separate call)
            try:
                # We try to get info, but if it fails/times out, we skip
                info = stock.info
                sector = info.get('sector', 'Unknown')
                # Sometimes sector is missing, try category or industry
                if sector == 'Unknown':
                    sector = info.get('category', 'Unknown')
            except:
                pass # Sector is not critical, don't crash

            # Save data
            price_data[ticker] = {
                'price': float(current_price) if current_price else 0.0,
                'prev_close': float(prev_close) if prev_close else 0.0,
                'sector': sector
            }
            
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            price_data[ticker] = {'price': 0.0, 'prev_close': 0.0, 'sector': 'Unknown'}
    
    return price_data

# --- Helper for SPY ---
def calculate_spy_return(start_date):
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        spy = yf.Ticker('SPY', session=session)
        hist = spy.history(start=start_date)
        if hist.empty: return 0.0
        start_p = hist['Close'].iloc[0]
        end_p = hist['Close'].iloc[-1]
        return ((end_p - start_p) / start_p) * 100
    except:
        return 0.0

# --- 4. Build Portfolio Table ---
def build_portfolio_table(holdings_df, price_data, cash_balance):
    if holdings_df.empty:
        return pd.DataFrame()
    
    rows = []
    for _, row in holdings_df.iterrows():
        ticker = row['Ticker']
        qty = row['Qty']
        avg = row['Avg_Buy_Price']
        
        data = price_data.get(ticker, {'price': 0, 'prev_close': 0, 'sector': 'Unknown'})
        curr = data['price']
        prev = data['prev_close']
        
        market_value = qty * curr
        
        # Total Return: (Current - Avg Buy) / Avg Buy
        total_return_pct = ((curr - avg) / avg * 100) if avg > 0 else 0
        
        # Daily Return: (Current - Prev Close) / Prev Close
        daily_return_pct = 0.0
        if prev > 0:
            daily_return_pct = ((curr - prev) / prev * 100)
        
        spy_ret = 0.0
        if row['First_Buy_Date'] is not None:
            spy_ret = calculate_spy_return(row['First_Buy_Date'])
            
        alpha = total_return_pct - spy_ret
        
        rows.append({
            'Ticker': ticker,
            'Qty': qty,
            'Avg Buy Price': avg,
            'Current Price': curr,
            'Market Value': market_value,
            'Total Return %': total_return_pct,
            'Daily Return %': daily_return_pct, # Now using real data
            'Alpha vs SPY': alpha,
            'Sector': data.get('sector', 'Unknown')
        })
        
    df = pd.DataFrame(rows)
    if not df.empty:
        total = df['Market Value'].sum() + cash_balance
        if total > 0:
            df['% of Portfolio'] = (df['Market Value'] / total * 100).round(2)
        else:
            df['% of Portfolio'] = 0.0
            
        cols = ['Ticker', 'Qty', 'Avg Buy Price', 'Current Price', 'Market Value', '% of Portfolio', 'Total Return %', 'Daily Return %', 'Alpha vs SPY', 'Sector']
        return df[cols]
    return pd.DataFrame()

# --- 5. Metrics ---
def calculate_portfolio_metrics(portfolio_df, cash_balance, transactions_df):
    if portfolio_df.empty:
        mkt_val = 0.0
        daily_pnl = 0.0
    else:
        mkt_val = portfolio_df['Market Value'].sum()
        # Calculate Real Daily P&L ($) based on daily return %
        daily_pnl = (portfolio_df['Market Value'] * (portfolio_df['Daily Return %'] / 100)).sum()
    
    invested = 0.0
    if not transactions_df.empty:
        for _, r in transactions_df.iterrows():
            t_type = str(r['Type']).strip()
            try:
                price = float(r['Price'])
            except:
                price = 0.0
                
            if t_type == 'Deposit Cash': invested += price
            elif t_type == 'Withdraw Cash': invested -= price
            
    total_val = mkt_val + cash_balance
    ret_dol = total_val - invested
    ret_pct = (ret_dol / invested * 100) if invested > 0 else 0.0
    
    return {
        'total_portfolio_value': total_val,
        'cash_balance': cash_balance,
        'total_return_dollars': ret_dol,
        'total_return_pct': ret_pct,
        'daily_pnl': daily_pnl
    }

# --- 6. Historical (Placeholder) ---
def calculate_historical_portfolio_value(transactions_df, start_date, end_date=None):
    return pd.DataFrame()

# --- 7. Sector ---
def get_sector_allocation(portfolio_df):
    if portfolio_df.empty or 'Sector' not in portfolio_df.columns:
        return pd.DataFrame()
    return portfolio_df.groupby('Sector')['Market Value'].sum().reset_index().rename(columns={'Market Value': 'Value'})
