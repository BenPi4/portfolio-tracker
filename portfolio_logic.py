"""
Portfolio calculation logic and helper functions.
Separates business logic from UI for cleaner code.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np


def calculate_cash_balance(transactions_df):
    """
    Calculate current cash balance from transaction history.
    
    Args:
        transactions_df: DataFrame with columns [Date, Ticker, Type, Quantity, Price]
    
    Returns:
        float: Current cash balance
    """
    cash = 0.0
    
    for _, row in transactions_df.iterrows():
        if row['Type'] == 'Deposit Cash':
            cash += row['Price']  # Price field used as deposit amount
        elif row['Type'] == 'Withdraw Cash':
            cash -= row['Price']  # Price field used as withdrawal amount
        elif row['Type'] == 'Buy':
            cash -= row['Quantity'] * row['Price']
        elif row['Type'] == 'Sell':
            cash += row['Quantity'] * row['Price']
    
    return cash


def get_current_holdings(transactions_df):
    """
    Calculate current holdings from transaction history.
    
    Args:
        transactions_df: DataFrame with transaction history
    
    Returns:
        DataFrame: Holdings with columns [Ticker, Qty, Avg_Buy_Price, First_Buy_Date]
    """
    holdings = {}
    
    # Filter only buy/sell transactions
    stock_transactions = transactions_df[
        transactions_df['Type'].isin(['Buy', 'Sell'])
    ].copy()
    
    for _, row in stock_transactions.iterrows():
        ticker = row['Ticker']
        
        if ticker not in holdings:
            holdings[ticker] = {
                'total_qty': 0,
                'total_cost': 0,
                'first_buy_date': None
            }
        
        if row['Type'] == 'Buy':
            holdings[ticker]['total_qty'] += row['Quantity']
            holdings[ticker]['total_cost'] += row['Quantity'] * row['Price']
            
            # Track first purchase date
            if holdings[ticker]['first_buy_date'] is None:
                holdings[ticker]['first_buy_date'] = pd.to_datetime(row['Date'])
            else:
                holdings[ticker]['first_buy_date'] = min(
                    holdings[ticker]['first_buy_date'],
                    pd.to_datetime(row['Date'])
                )
        
        elif row['Type'] == 'Sell':
            holdings[ticker]['total_qty'] -= row['Quantity']
            # Proportionally reduce cost basis
            if holdings[ticker]['total_qty'] > 0:
                avg_price = holdings[ticker]['total_cost'] / (holdings[ticker]['total_qty'] + row['Quantity'])
                holdings[ticker]['total_cost'] = holdings[ticker]['total_qty'] * avg_price
            else:
                holdings[ticker]['total_cost'] = 0
    
    # Convert to DataFrame and filter out zero positions
    holdings_list = []
    for ticker, data in holdings.items():
        if data['total_qty'] > 0:
            holdings_list.append({
                'Ticker': ticker,
                'Qty': data['total_qty'],
                'Avg_Buy_Price': data['total_cost'] / data['total_qty'],
                'First_Buy_Date': data['first_buy_date']
            })
    
    return pd.DataFrame(holdings_list) if holdings_list else pd.DataFrame()


def fetch_live_prices(tickers):
    """
    Fetch current prices and sector info for a list of tickers.
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        dict: {ticker: {'price': float, 'prev_close': float, 'sector': str}}
    """
    price_data = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period='2d')
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price is None and len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
            
            prev_close = info.get('previousClose')
            if prev_close is None and len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
            
            price_data[ticker] = {
                'price': current_price,
                'prev_close': prev_close,
                'sector': info.get('sector', 'Unknown')
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            price_data[ticker] = {
                'price': 0,
                'prev_close': 0,
                'sector': 'Unknown'
            }
    
    return price_data


def calculate_spy_return(start_date, end_date=None):
    """
    Calculate SPY return over a specific period.
    
    Args:
        start_date: Start date for calculation
        end_date: End date (default: today)
    
    Returns:
        float: SPY return percentage
    """
    if end_date is None:
        end_date = datetime.now()
    
    try:
        spy = yf.Ticker('SPY')
        hist = spy.history(start=start_date, end=end_date)
        
        if len(hist) < 2:
            return 0.0
        
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        
        return ((end_price - start_price) / start_price) * 100
    except Exception as e:
        print(f"Error calculating SPY return: {e}")
        return 0.0


def build_portfolio_table(holdings_df, price_data, cash_balance):
    """
    Build the main portfolio table with all metrics.
    
    Args:
        holdings_df: DataFrame with current holdings
        price_data: Dict with live price data
        cash_balance: Current cash balance
    
    Returns:
        DataFrame: Complete portfolio table with all metrics
    """
    if holdings_df.empty:
        return pd.DataFrame()
    
    portfolio_rows = []
    
    for _, holding in holdings_df.iterrows():
        ticker = holding['Ticker']
        qty = holding['Qty']
        avg_price = holding['Avg_Buy_Price']
        first_buy_date = holding['First_Buy_Date']
        
        # Get live data
        live_data = price_data.get(ticker, {})
        current_price = live_data.get('price', 0)
        prev_close = live_data.get('prev_close', current_price)
        sector = live_data.get('sector', 'Unknown')
        
        # Calculate metrics
        market_value = qty * current_price
        total_return_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        daily_return_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
        
        # Calculate Alpha vs SPY
        spy_return = calculate_spy_return(first_buy_date)
        alpha = total_return_pct - spy_return
        
        portfolio_rows.append({
            'Ticker': ticker,
            'Qty': qty,
            'Avg Buy Price': avg_price,
            'Current Price': current_price,
            'Market Value': market_value,
            'Total Return %': total_return_pct,
            'Daily Return %': daily_return_pct,
            'Alpha vs SPY': alpha,
            'Sector': sector
        })
    
    portfolio_df = pd.DataFrame(portfolio_rows)
    
    # Calculate portfolio allocation
    total_portfolio_value = portfolio_df['Market Value'].sum() + cash_balance
    portfolio_df['% of Portfolio'] = (portfolio_df['Market Value'] / total_portfolio_value * 100).round(2)
    
    # Reorder columns
    column_order = [
        'Ticker', 'Qty', 'Avg Buy Price', 'Current Price', 
        'Market Value', '% of Portfolio', 'Total Return %', 
        'Daily Return %', 'Alpha vs SPY'
    ]
    
    return portfolio_df[column_order]


def calculate_portfolio_metrics(portfolio_df, cash_balance, transactions_df):
    """
    Calculate top-level portfolio metrics (KPIs).
    
    Args:
        portfolio_df: Portfolio table
        cash_balance: Current cash
        transactions_df: Transaction history
    
    Returns:
        dict: Portfolio metrics
    """
    if portfolio_df.empty:
        total_market_value = 0
        total_cost_basis = 0
        daily_pnl = 0
    else:
        total_market_value = portfolio_df['Market Value'].sum()
        
        # Calculate total cost basis from transactions
        buy_transactions = transactions_df[transactions_df['Type'] == 'Buy'].copy()
        total_cost_basis = (buy_transactions['Quantity'] * buy_transactions['Price']).sum()
        
        # Calculate daily P&L
        daily_pnl = (portfolio_df['Market Value'] * 
                     (portfolio_df['Daily Return %'] / 100)).sum()
    
    total_portfolio_value = total_market_value + cash_balance
    total_return_dollars = total_market_value - total_cost_basis
    total_return_pct = (total_return_dollars / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    return {
        'total_portfolio_value': total_portfolio_value,
        'cash_balance': cash_balance,
        'total_return_dollars': total_return_dollars,
        'total_return_pct': total_return_pct,
        'daily_pnl': daily_pnl
    }


def calculate_historical_portfolio_value(transactions_df, start_date, end_date=None):
    """
    Reconstruct daily portfolio value from transaction history.
    
    Args:
        transactions_df: Transaction history
        start_date: Start date for reconstruction
        end_date: End date (default: today)
    
    Returns:
        DataFrame: Columns [Date, Portfolio_Value, SPY_Value]
    """
    if end_date is None:
        end_date = datetime.now()
    
    # Get all unique tickers
    tickers = transactions_df[
        transactions_df['Type'].isin(['Buy', 'Sell'])
    ]['Ticker'].unique().tolist()
    
    if not tickers:
        return pd.DataFrame()
    
    # Download historical data for all tickers + SPY
    all_tickers = tickers + ['SPY']
    
    try:
        price_history = yf.download(
            all_tickers, 
            start=start_date, 
            end=end_date,
            progress=False
        )['Close']
        
        if isinstance(price_history, pd.Series):
            price_history = price_history.to_frame()
        
        # Ensure SPY is included
        if 'SPY' not in price_history.columns:
            spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)['Close']
            price_history['SPY'] = spy_data
    except Exception as e:
        print(f"Error downloading historical data: {e}")
        return pd.DataFrame()
    
    # Calculate daily holdings
    daily_values = []
    
    for date in price_history.index:
        # Get holdings as of this date
        trans_up_to_date = transactions_df[
            pd.to_datetime(transactions_df['Date']) <= date
        ]
        
        holdings = get_current_holdings(trans_up_to_date)
        cash = calculate_cash_balance(trans_up_to_date)
        
        # Calculate portfolio value
        portfolio_value = cash
        
        for _, holding in holdings.iterrows():
            ticker = holding['Ticker']
            qty = holding['Qty']
            
            if ticker in price_history.columns:
                price = price_history.loc[date, ticker]
                if not pd.isna(price):
                    portfolio_value += qty * price
        
        # Get SPY value for comparison
        spy_price = price_history.loc[date, 'SPY']
        
        daily_values.append({
            'Date': date,
            'Portfolio_Value': portfolio_value,
            'SPY_Price': spy_price
        })
    
    daily_df = pd.DataFrame(daily_values)
    
    # Calculate cumulative returns
    if not daily_df.empty and len(daily_df) > 0:
        initial_portfolio = daily_df['Portfolio_Value'].iloc[0]
        initial_spy = daily_df['SPY_Price'].iloc[0]
        
        daily_df['Portfolio_Return_%'] = (
            (daily_df['Portfolio_Value'] - initial_portfolio) / initial_portfolio * 100
        )
        daily_df['SPY_Return_%'] = (
            (daily_df['SPY_Price'] - initial_spy) / initial_spy * 100
        )
    
    return daily_df


def get_sector_allocation(portfolio_df):
    """
    Calculate portfolio allocation by sector.
    
    Args:
        portfolio_df: Portfolio table with Sector column
    
    Returns:
        DataFrame: Sector allocation
    """
    if portfolio_df.empty or 'Sector' not in portfolio_df.columns:
        return pd.DataFrame()
    
    sector_allocation = portfolio_df.groupby('Sector')['Market Value'].sum().reset_index()
    sector_allocation.columns = ['Sector', 'Value']
    sector_allocation = sector_allocation.sort_values('Value', ascending=False)
    
    return sector_allocation
