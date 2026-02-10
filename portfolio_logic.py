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

# --- 3. Live Prices (The Hybrid Bulletproof Fix) ---
def fetch_live_prices(tickers):
    """
    Fetches 5 days of history in bulk to guarantee Prices + Daily Returns.
    Only attempts Sector individually (and fails silently if needed).
    """
    price_data = {}
    if not tickers:
        return price_data
    
    try:
        # 1. BULK DOWNLOAD - This guarantees we get prices (like before)
        # We ask for 5 days to handle weekends/holidays easily
        data = yf.download(tickers, period="5d", progress=False)
        
        # Check if we got data
        if 'Close' in data.columns:
            closes = data['Close']
            
            for ticker in tickers:
                current_price = 0.0
                prev_close = 0.0
                sector = 'Unknown'
                
                # --- A. Get Price & Daily Return from Bulk Data ---
                try:
                    # Handle Single Ticker vs Multiple Tickers structure
                    if isinstance(closes, pd.Series):
                        ticker_history = closes # It is just one series
                    elif isinstance(closes, pd.DataFrame) and ticker in closes.columns:
                        ticker_history = closes[ticker]
                    else:
                        ticker_history = pd.Series()

                    # Drop NaNs to get real trading days
                    ticker_history = ticker_history.dropna()
                    
                    if not ticker_history.empty:
                        current_price = float(ticker_history.iloc[-1])
                        
                        if len(ticker_history) >= 2:
                            prev_close = float(ticker_history.iloc[-2])
                        else:
                            prev_close = current_price # Fallback
                except:
                    # If parsing failed, keep 0
                    pass
                
                # --- B. Get Sector (Optional - Don't crash price if this fails) ---
                if current_price > 0:
                    try:
                        # We use a trick: only fetch info if we already succeeded in getting price
                        # This minimizes API calls.
                        info = yf.Ticker(ticker).info
                        sector = info.get('sector', 'Unknown')
                        if sector == 'Unknown':
                            sector = info.get('category', 'Unknown')
                    except:
                        pass # Sector remains 'Unknown', but PRICE IS SAFE
                
                # Store Data
                price_data[ticker] = {
                    'price': current_price,
                    'prev_close': prev_close,
                    'sector': sector
                }
        else:
            # Structure unexpected
            for ticker in tickers:
                price_data[ticker] = {'price': 0.0, 'prev_close': 0.0, 'sector': 'Unknown'}
                
    except Exception as e:
        print(f"Critical Error in fetch_live_prices: {e}")
        # Emergency fallback
        for ticker in tickers:
            price_data[ticker] = {'price': 0.0, 'prev_close': 0.0, 'sector': 'Unknown'}
    
    return price_data

# --- Helper for SPY ---
def calculate_spy_return(start_date):
    try:
        data = yf.download('SPY', start=start_date, progress=False)['Close']
        if data.empty: return 0.0
        start_p = float(data.iloc[0])
        end_p = float(data.iloc[-1])
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
            'Daily Return %': daily_return_pct, 
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
        # Daily PnL based on the daily return % we calculated
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
