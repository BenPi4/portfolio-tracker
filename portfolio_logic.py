import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta  
import requests
import smtplib
import ssl
from email.message import EmailMessage
import time
import threading

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
        elif t_type == 'Initial':
            # Initial Setup does not affect cash balance
            pass
    
    return cash

# --- 2. Holdings ---
def get_current_holdings(transactions_df):
    holdings = {}
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Include 'Initial' as a valid holding acquisition
    stock_transactions = transactions_df[
        transactions_df['Type'].isin(['Buy', 'Sell', 'Initial'])
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

        t_type = str(row['Type']).strip()
        
        # 'Initial' behaves exactly like 'Buy' for holdings calculations
        if t_type == 'Buy' or t_type == 'Initial':
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
        # 1. BULK DOWNLOAD - This guarantees we get prices
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
                    if isinstance(closes, pd.Series):
                        ticker_history = closes
                    elif isinstance(closes, pd.DataFrame) and ticker in closes.columns:
                        ticker_history = closes[ticker]
                    else:
                        ticker_history = pd.Series()

                    ticker_history = ticker_history.dropna()
                    
                    if not ticker_history.empty:
                        current_price = float(ticker_history.iloc[-1])
                        
                        if len(ticker_history) >= 2:
                            prev_close = float(ticker_history.iloc[-2])
                        else:
                            prev_close = current_price
                except:
                    pass
                
                # --- B. Get Sector (Optional) ---
                if current_price > 0:
                    try:
                        info = yf.Ticker(ticker).info
                        sector = info.get('sector', 'Unknown')
                        if sector == 'Unknown':
                            sector = info.get('category', 'Unknown')
                    except:
                        pass
                
                # Store Data
                price_data[ticker] = {
                    'price': current_price,
                    'prev_close': prev_close,
                    'sector': sector
                }
        else:
            for ticker in tickers:
                price_data[ticker] = {'price': 0.0, 'prev_close': 0.0, 'sector': 'Unknown'}
                
    except Exception as e:
        print(f"Critical Error in fetch_live_prices: {e}")
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


def validate_ticker(ticker):
    """
    Checks if a ticker is valid and returns unique Uppercase symbol.
    Returns (True, Ticker) or (False, ErrorMsg).
    """
    ticker = ticker.strip().upper()
    if not ticker: return False, "Empty Ticker"
    
    if ticker == 'CASH': return True, 'CASH'
    
    try:
        # Quick check using Ticker.info or history
        # History is safer/faster than info which downloads a lot of JSON
        t = yf.Ticker(ticker)
        # Fetch 1 day of history to verify existence
        hist = t.history(period='1d')
        if hist.empty:
            return False, f"Invalid Ticker: {ticker}"
        return True, ticker
    except:
        return False, f"Error validating {ticker}"

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
        
        # Total Return
        total_return_pct = ((curr - avg) / avg * 100) if avg > 0 else 0
        
        # Daily Return
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
        # Fix: For asset allocation %, use Total Assets (ignoring negative cash/margin)
        # This prevents holdings from showing > 100% allocation
        total_assets = df['Market Value'].sum() + max(0, cash_balance)
        
        if total_assets > 0:
            df['% of Portfolio'] = (df['Market Value'] / total_assets * 100).round(2)
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

# --- 6. Historical Performance Calculation (Robust Bulk Fix) ---
def calculate_historical_portfolio_value(transactions_df, start_date, end_date=None):
    """
    Reconstruct daily portfolio value using bulk download (safest against blocks).
    """
    if transactions_df.empty:
        return pd.DataFrame()

    if end_date is None:
        end_date = datetime.now()

    # 1. Prepare Tickers
    tickers = transactions_df['Ticker'].unique().tolist()
    if 'CASH' in tickers:
        tickers.remove('CASH')
    
    # Always add SPY for comparison
    if 'SPY' not in tickers:
        tickers.append('SPY')

    # 2. Download ALL history at once (Much faster & avoids bans)
    # We buffer the start date by 10 days to ensure we have data for the start
    safe_start = pd.to_datetime(start_date) - timedelta(days=10)
    
    try:
        # threads=False is safer for Streamlit Cloud
        raw_data = yf.download(tickers, start=safe_start, end=end_date, progress=False, threads=False)
    except Exception as e:
        print(f"Download failed: {e}")
        return pd.DataFrame()

    # 3. Process the downloaded data structure
    price_data = pd.DataFrame()

    try:
        # Scenario A: Multiple Tickers (returns MultiIndex columns)
        if isinstance(raw_data.columns, pd.MultiIndex):
            if 'Close' in raw_data.columns:
                price_data = raw_data['Close']
            else:
                return pd.DataFrame() # Data format unexpected
        
        # Scenario B: Single Ticker (returns Flat columns: Open, High, Low, Close)
        else:
            if 'Close' in raw_data.columns:
                # If we asked for 1 ticker, this IS the data for that ticker
                # We need to rename 'Close' to the ticker symbol
                ticker_name = tickers[0] 
                price_data = raw_data[['Close']].copy()
                price_data.columns = [ticker_name]
            else:
                return pd.DataFrame()
                
    except Exception as e:
        print(f"Data processing failed: {e}")
        return pd.DataFrame()

    if price_data.empty:
        return pd.DataFrame()

    # 4. Reconstruct Portfolio Value Day by Day
    # Handle timezone issues
    price_data.index = price_data.index.tz_localize(None)
    dates = price_data.index
    
    trans_sorted = transactions_df.sort_values('Date')
    history_records = []
    
    for date in dates:
        # Ignore dates before our actual requested start (due to the 10-day buffer)
        if date < pd.to_datetime(start_date):
            continue

        # Transactions up to this day
        current_trans = trans_sorted[trans_sorted['Date'] <= date]
        
        if current_trans.empty:
            continue
            
        cash = calculate_cash_balance(current_trans)
        holdings = get_current_holdings(current_trans)
        
        portfolio_val = cash
        
        if not holdings.empty:
            for _, row in holdings.iterrows():
                t = row['Ticker']
                q = row['Qty']
                
                # Check if we have price data for this ticker
                if t in price_data.columns:
                    price = price_data.loc[date, t]
                    
                    # Fix NaNs (Forward Fill logic manually)
                    if pd.isna(price):
                        # Look at previous 5 days
                        prev_days = price_data[t].loc[:date].tail(6)[:-1] # Exclude current
                        if not prev_days.empty:
                             valid_prev = prev_days.dropna()
                             if not valid_prev.empty:
                                 price = valid_prev.iloc[-1]
                             else:
                                 price = 0.0
                        else:
                             price = 0.0
                    
                    portfolio_val += float(q) * float(price)
        
        # Get SPY value
        spy_val = 0.0
        if 'SPY' in price_data.columns:
            spy_val = price_data.loc[date, 'SPY']
            if pd.isna(spy_val):
                 valid_spy = price_data['SPY'].loc[:date].dropna()
                 if not valid_spy.empty:
                     spy_val = valid_spy.iloc[-1]

        history_records.append({
            'Date': date,
            'Portfolio_Value': portfolio_val,
            'SPY_Price': spy_val
        })
    
    # 5. Final Output
    history_df = pd.DataFrame(history_records)
    
    if history_df.empty:
        return pd.DataFrame()

    # Normalize to Percentage Return (Starting at 0%)
    initial_port = history_df['Portfolio_Value'].iloc[0]
    initial_spy = history_df['SPY_Price'].iloc[0]
    
    if initial_port > 0:
        history_df['Portfolio_Return_%'] = (history_df['Portfolio_Value'] - initial_port) / initial_port * 100
    else:
        history_df['Portfolio_Return_%'] = 0.0
        
    if initial_spy > 0:
        history_df['SPY_Return_%'] = (history_df['SPY_Price'] - initial_spy) / initial_spy * 100
    else:
        history_df['SPY_Return_%'] = 0.0
        
    return history_df
    
# --- 7. Sector ---
def get_sector_allocation(portfolio_df):
    if portfolio_df.empty or 'Sector' not in portfolio_df.columns:
        return pd.DataFrame()
    return portfolio_df.groupby('Sector')['Market Value'].sum().reset_index().rename(columns={'Market Value': 'Value'})

# --- 8. Alert System ---
def ensure_alerts_sheet(client, sheet_name="Alerts"):
    """
    Checks if 'Alerts' worksheet exists. If not, creates it with headers.
    Returns the worksheet object.
    """
    try:
        sh = client.open_by_key(client.list_spreadsheet_files()[0]['id']) # Assuming first sheet or pass spreadsheet object
        # Better approach: pass the spreadsheet object or name if possible, but manager.py handles client.
        # However, portfolio_logic functions usually take dataframes. 
        # But here we need to interact with the sheet directly to create/update.
        # Let's assume 'client' here is the gspread client or we need a way to get the spreadsheet.
        # Refactoring note: Manager manages the client. tailored for portfolio_logic to be pure logic?
        # The user requested adding this TO portfolio_logic.py. 
        # But for 'client' interaction it might be better in manager.py or pass the sheet object.
        # Implementation: We will write the logic here but it requires the gspread 'spreadsheet' object or 'client'.
        # Let's assume we pass the 'spreadsheet' object.
        pass
    except:
        pass

# Redefining to use in Manager or App, but user asked for logic here.
# Let's implement the pure logic and helpers here, and the gspread interaction might need to be in manager
# or we pass the gspread wrappers. 
# Actually, looking at the code, portfolio_logic is mostly pandas logic. 
# But the request explicitly asked to add "Self-Healing Google Sheet" function to `portfolio_logic.py`.
# So I will implement it here, assuming `spreadsheet` is passed.

def check_and_create_alerts_sheet(spreadsheet):
    try:
        worksheet = spreadsheet.worksheet("Alerts")
    except:
        worksheet = spreadsheet.add_worksheet(title="Alerts", rows=100, cols=10)
        # New Headers: [Ticker, Target Price, Direction, Subscribers, Status, Note]
        worksheet.append_row(["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"])
    return worksheet

def send_alert_email(ticker, price, direction, subscribers, sender_creds):
    """
    Sends email to a list of subscribers.
    subscribers: list of email strings
    """
    sender_email = sender_creds.get('user')
    password = sender_creds.get('password')
    
    if not sender_email or not password:
        return False
        
    # Remove duplicates and cleanup
    recipients = list(set([s.strip() for s in subscribers if '@' in s]))
    
    if not recipients:
        return False

    msg = EmailMessage()
    msg.set_content(f"🚀 ALERT TRIGGERED!\n\nTicker: {ticker}\nCondition: {direction} ${price:.2f}\n\nCurrent Price: ${price:.2f}\n\nHappy Trading!")
    msg['Subject'] = f"🔔 Alert: {ticker} hit ${price:.2f}"
    msg['From'] = sender_email
    msg['Bcc'] = ", ".join(recipients) # Use Bcc to hide other subscribers
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def process_alerts(spreadsheet, email_creds):
    """
    Checks alerts and sends emails to subscribers. 
    """
    ws = check_and_create_alerts_sheet(spreadsheet)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty: return
    
    # Check for required columns (handling migration somewhat gracefully or just failing)
    required = ["Ticker", "Target Price", "Direction", "Subscribers", "Status"]
    if not all(col in df.columns for col in required):
        # If headers are mismatch, might need manual fix or we skip
        # For now, let's assume they are correct as per plan
        return

    triggered_count = 0
    
    # Fetch live prices for all tickers in alerts
    tickers = df['Ticker'].unique().tolist()
    if not tickers: return
    
    prices = fetch_live_prices(tickers)
    
    for i, row in df.iterrows():
        ticker = row['Ticker']
        try:
            target = float(row['Target Price'])
        except:
            continue
            
        direction = row['Direction']
        status = row['Status']
        subscribers_str = str(row['Subscribers'])
        
        # If already sent, skip (Global Status)
        if str(status).lower() == "sent":
            continue
            
        current_price = prices.get(ticker, {}).get('price', 0)
        if current_price == 0: continue
        
        hit = False
        if direction == "Above" and current_price >= target:
            hit = True
        elif direction == "Below" and current_price <= target:
            hit = True
            
        if hit:
            # Parse subscribers
            subs_list = subscribers_str.split(',')
            
            # Send Email to all subscribers
            sent = send_alert_email(ticker, current_price, direction, subs_list, email_creds)
            
            if sent:
                # Update row status to Sent
                # gspread is 1-indexed, header is row 1, so data row i is i+2
                # Status is column 5, Last Checked is column 7 (based on new headers)
                # Let's find column index dynamically if possible or hardcode based on check_and_create
                # Headers: ["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"]
                # Status is col 5
                
                try:
                    # Find 'Status' column index
                    status_col = df.columns.get_loc("Status") + 1
                    last_checked_col = df.columns.get_loc("Last Checked") + 1
                    
                    ws.update_cell(i + 2, status_col, "Sent")
                    ws.update_cell(i + 2, last_checked_col, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                except:
                    # Fallback hardcoded if columns align
                    ws.update_cell(i + 2, 5, "Sent") 
                
                triggered_count += 1



def reset_all_alerts(spreadsheet):
    ws = check_and_create_alerts_sheet(spreadsheet)
    data = ws.get_all_records()
    if not data: return
    
    # Get range of Status column. 
    # Need to dynamically find it since headers changed
    try:
        headers = ws.row_values(1)
        status_idx = headers.index("Status") + 1
        col_letter = gspread.utils.rowcol_to_a1(1, status_idx)[0] # simple check, might bug if > 26 cols
        # Better: just use iteration or find by name. 
        # Update: We know it's column 5 in new schema but let's be safe.
        
        cell_list = ws.range(f"{col_letter}2:{col_letter}{len(data)+1}")
        for cell in cell_list:
            cell.value = "Active"
        ws.update_cells(cell_list)
    except:
        pass

def reactivate_alert(spreadsheet, row_index):
    """
    Sets the status of a specific alert row back to 'Active'.
    """
    try:
        ws = check_and_create_alerts_sheet(spreadsheet)
        # Headers: ["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"]
        # Status is col 5
        sheet_row = row_index + 2
        
        ws.update_cell(sheet_row, 5, "Active")
        return True, "Alert reactivated!"
    except Exception as e:
        return False, f"Failed to reactivate: {e}"

def delete_alert_row(spreadsheet, row_index):
    """
    Deletes a specific row from the Alerts sheet.
    row_index is 0-based dataframe index, so we need to convert to 1-based sheet index.
    Sheet has headers, so data starts at row 2.
    Row in DF index 0 is Sheet Row 2.
    """
    try:
        ws = check_and_create_alerts_sheet(spreadsheet)
        # Convert 0-based index to 1-based row number
        # DF Index 0 -> Sheet Row 2
        sheet_row = row_index + 2
        ws.delete_rows(sheet_row)
        return True, "Alert deleted."
    except Exception as e:
        return False, f"Failed to delete: {e}"

def unsubscribe_from_alert(spreadsheet, row_index, user_email):
    """
    Removes user_email from the subscribers list of a specific row.
    """
    try:
        ws = check_and_create_alerts_sheet(spreadsheet)
        # Headers: ["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"]
        # Subscribers is column 4 (D)
        sheet_row = row_index + 2
        
        current_subs = ws.cell(sheet_row, 4).value
        
        if not current_subs: return True, "Already unsubscribed."
        
        subs_list = [s.strip() for s in str(current_subs).split(',') if s.strip()]
        
        if user_email in subs_list:
            subs_list.remove(user_email)
            new_subs = ",".join(subs_list)
            ws.update_cell(sheet_row, 4, new_subs)
            return True, "Unsubscribed successfully."
        else:
            return True, "You were not subscribed."
            
    except Exception as e:
        return False, f"Failed to unsubscribe: {e}"

def subscribe_to_alert(spreadsheet, row_index, user_email):
    """
    Adds user_email to the subscribers list of a specific row.
    """
    try:
        ws = check_and_create_alerts_sheet(spreadsheet)
        # Headers: ["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"]
        # Subscribers is column 4 (D)
        sheet_row = row_index + 2
        
        current_subs = ws.cell(sheet_row, 4).value
        
        if not current_subs: 
            # If empty, just set it
            new_subs = user_email
        else:
            subs_list = [s.strip() for s in str(current_subs).split(',') if s.strip()]
            if user_email in subs_list:
                return True, "Already subscribed."
            
            subs_list.append(user_email)
            new_subs = ",".join(subs_list)
            
        ws.update_cell(sheet_row, 4, new_subs)
        return True, "Subscribed successfully!"
            
    except Exception as e:
        return False, f"Failed to subscribe: {e}"

def send_test_email(creds, receiver_email="ben636569@gmail.com"):
    """
    Sends a simple test email to verify credentials.
    """
    sender = creds.get('user')
    password = creds.get('password')
    
    if not sender or not password:
        return False, "Missing credentials"
        
    msg = EmailMessage()
    msg.set_content("This is a test email from your Portfolio Tracker. 🚀\n\nIf you see this, the alert system is ready to go!")
    msg['Subject'] = "✅ Portfolio Tracker: Test Email"
    msg['From'] = sender
    msg['To'] = receiver_email
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)

