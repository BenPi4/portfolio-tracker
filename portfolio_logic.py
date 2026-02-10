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
    """
    cash = 0.0
    
    for _, row in transactions_df.iterrows():
        t_type = str(row['Type']).strip()
        price = float(row['Price'])
        quantity = float(row['Quantity'])

        if t_type == 'Deposit Cash':
            cash += price
        elif t_type == 'Withdraw Cash':
            cash -= price
        elif t_type == 'Buy':
            cash -= quantity * price
        elif t_type == 'Sell':
            cash += quantity * price
    
    return cash


def get_current_holdings(transactions_df):
    """
    Calculate current holdings from transaction history.
    """
    holdings = {}
    
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
    
    # Convert to DataFrame and filter out zero positions
    holdings_
