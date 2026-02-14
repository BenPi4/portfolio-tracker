import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import threading
import time
import traceback
import traceback
from portfolio_manager import PortfolioManager

# --- IMPORT LOGIC FROM HELPER FILE ---
from portfolio_logic import (
    calculate_cash_balance,
    get_current_holdings,
    fetch_live_prices,
    build_portfolio_table,
    calculate_portfolio_metrics,
    calculate_historical_portfolio_value,
    get_sector_allocation,
    process_alerts,
    reset_all_alerts,
    check_and_create_alerts_sheet,
    send_test_email,
    validate_ticker,
    delete_alert_row,
    unsubscribe_from_alert,
    subscribe_to_alert,
    reactivate_alert
)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)



# --- INITIALIZE MANAGER ---
@st.cache_resource
def get_portfolio_manager_v2():
    # 1. Check Local File First
    if os.path.exists('credentials.json'):
        return PortfolioManager('credentials.json')

    # 2. Check Secrets Second
    try:
        # Accessing st.secrets might raise FileNotFoundError if no secrets file exists
        if "gcp_service_account" in st.secrets:
            return PortfolioManager(dict(st.secrets["gcp_service_account"]))
    except (FileNotFoundError, KeyError):
        pass
    except Exception as e:
        # specific Streamlit error for secrets not found might vary, generic catch is safer for fallback
        pass

    # 3. Fallback
    st.error("Credentials not found. Please provide 'credentials.json' locally or configure Streamlit secrets.")
    st.stop()

    st.stop()

manager = get_portfolio_manager_v2()

# --- BACKGROUND ALERTS THREAD ---
def start_alert_monitor():
    if 'alert_thread_started' not in st.session_state:
        st.session_state.alert_thread_started = True
        
        def run_check():
            while True:
                try:
                    # Credentials for Email (Updated to match user request)
                    # Using nested calls or get to avoid keyerrors if not set
                    try:
                        email_creds = {
                            'user': st.secrets["email"]["user"],
                            'password': st.secrets["email"]["password"]
                        }
                    except:
                        # Fallback or silent fail if secrets not set yes
                        print("Email secrets not found")
                        time.sleep(300)
                        continue

                    if manager and manager.client:
                        try:
                             # FIXED: Use ID from manager meant for this
                             spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
                             
                             # Adapt keys for process_alerts which expects specific keys if I named them differently?
                             # In portfolio_logic.py: send_alert_email_with_creds uses 'email' and 'password'.
                             # I should map them.
                             creds_for_func = {
                                 'email': email_creds['user'],
                                 'password': email_creds['password']
                             }
                             process_alerts(spreadsheet, creds_for_func)
                        except Exception as e:
                            print(f"Alert Loop Error: {e}")
                            traceback.print_exc()
                            
                except Exception as e:
                    print(f"Thread Error: {e}")
                
                # Sleep for 30 minutes
                time.sleep(1800) 

        # Daemon thread so it dies when main thread dies (though Streamlit management is tricky)
        t = threading.Thread(target=run_check, daemon=True)
        t.start()

start_alert_monitor()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_tab' not in st.session_state: st.session_state.user_tab = None
if 'alerts_tab' not in st.session_state: st.session_state.alerts_tab = None
if 'user_email' not in st.session_state: st.session_state.user_email = "" # Initialize email

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

def update_user_transactions(df):
    """
    Overwrites the user's transaction sheet with the provided DataFrame.
    Used for Edit Mode.
    """
    try:
        # Prepare data
        update_data = []
        # Headers
        update_data.append(["Date", "Ticker", "Type", "Quantity", "Price"])
        
        for _, row in df.iterrows():
            d = row['Date']
            if isinstance(d, pd.Timestamp):
                d = d.strftime('%Y-%m-%d')
            else:
                d = str(d)
                
            update_data.append([
                d,
                str(row['Ticker']),
                str(row['Type']),
                float(row['Quantity']),
                float(row['Price'])
            ])
            
        st.session_state.user_tab.clear()
        st.session_state.user_tab.update('A1', update_data)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update sheet: {e}")
        return False

def load_alerts():
    try:
        # Load from Global Alerts Sheet via Manager (or reconstruct)
        # We need the "Alerts" sheet from the spreadsheet.
        # FIXED: Use ID
        spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
        print(f"LOAD ALERTS: Accessing Spreadsheet: {spreadsheet.title}")
        
        ws = check_and_create_alerts_sheet(spreadsheet)
        print(f"LOAD ALERTS: Accessing Worksheet: {ws.title}")
        
        data = ws.get_all_records()
        if not data:
            print("Alerts sheet found but no data rows")
        else:
            print(f"Alerts loaded: {len(data)} rows")
            
        return pd.DataFrame(data)
    except Exception as e:
        print(f"LOAD ALERTS ERROR: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def add_alert_to_sheet(ticker, target, condition, note=""):
    try:
        # FIXED: Use ID from manager
        spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
        print(f"ADD ALERT: Target Spreadsheet: {spreadsheet.title}")
        
        ws = check_and_create_alerts_sheet(spreadsheet)
        print(f"ADD ALERT: Target Sheet: {ws.title}")
        
        # Headers: ["Ticker", "Target Price", "Direction", "Subscribers", "Status", "Note", "Last Checked"]
        user_email = st.session_state.user_email
        new_row = [ticker, target, condition, user_email, "Active", note, "Never"]
        
        print(f"ADD ALERT: Data being sent: {new_row}")
        
        ws.append_row(new_row)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"ADD ALERT ERROR: {e}")
        traceback.print_exc()
        return False

# --- CHARTING FUNCTIONS ---
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
    
    # 1. Prepare Data: Holdings Chart (Top 6 + Other)
    # Ensure Market Value is numeric
    portfolio_df['Market Value'] = pd.to_numeric(portfolio_df['Market Value'], errors='coerce').fillna(0)
    
    # Sort by Market Value Descending
    sorted_df = portfolio_df.sort_values(by='Market Value', ascending=False)
    
    # Extract Top 6
    top_6 = sorted_df.head(6)[['Ticker', 'Market Value']].copy()
    
    # Calculate 'Other'
    remaining = sorted_df.iloc[6:]
    other_value = remaining['Market Value'].sum()
    
    # Create DataFrames to combine
    parts = [top_6]
    
    if other_value > 0:
        parts.append(pd.DataFrame([{'Ticker': 'Other', 'Market Value': other_value}]))
        
    if cash_balance > 0:
        parts.append(pd.DataFrame([{'Ticker': 'Cash', 'Market Value': cash_balance}]))
        
    holdings_processed = pd.concat(parts, ignore_index=True)
    
    fig1 = px.pie(holdings_processed, values='Market Value', names='Ticker', title='Holdings', hole=0.5)
    
    # 2. Prepare Data: Sector Chart
    sector_data = get_sector_allocation(portfolio_df)
    fig2 = None
    if not sector_data.empty:
        fig2 = px.pie(sector_data, values='Value', names='Sector', title='Sectors', hole=0.5)

    # Apply Consistent Styling to Both Charts
    for fig in [fig1, fig2]:
        if fig:
            fig.update_traces(
                textposition='inside',
                textinfo='percent',
                texttemplate='%{percent:.2%}',
                hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Share: %{percent:.2%}'
            )
            fig.update_layout(
                uniformtext_minsize=10, 
                uniformtext_mode='hide', 
                showlegend=True,
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor='center'),
                margin=dict(t=40, b=40, l=20, r=20),
                height=350
            )
            
    return fig1, fig2

# ==========================================
#               MAIN APP LOGIC
# ==========================================

if not st.session_state.logged_in:
    st.title("Portfolio Tracker")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            # Update Login to get email too (need to update manager.py too ideally, but here we can cheat or assume manager returns it if we modify manager)
            # Actually, I need to modify manager.py to return email? 
            # Reviewing manager.py: "return True, trans_tab, alerts_tab"
            # It reads record.get('Email')? 
            # I should view manager.py again to see where email is stored. 
            # It stores user_email in col 4. 
            # But login function doesn't return it currently.
            # I must modify manager.py to return email.
            # OR I can just fetch it here if I had access, but manager encapsulates it.
            # Let's Modify manager.py first? 
            # Wait, I am in app.py step. I can do it in next step or assuming manager returns 4 values.
            # Let's assume I will update manager.py to return (success, user_tab, alerts_tab, email)
            
            # DEBUGGING LOGIN
            try:
                # print(f"DEBUG: manager type: {type(manager)}") 
                login_result = manager.login(u, p)
                print(f"DEBUG: login result length: {len(login_result)}")
                print(f"DEBUG: login result: {login_result}")
                
                success, user_tab, alerts_tab, user_email = login_result
                
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_tab = user_tab
                    st.session_state.alerts_tab = alerts_tab
                    st.session_state.user_email = user_email
                    st.rerun()
                else: st.error("Login failed")
            except ValueError as ve:
                st.error(f"Login Error: {ve}")
                if 'login_result' in locals():
                    st.write(f"Received {len(login_result)} values: {login_result}")
            except Exception as e:
                st.error(f"Unexpected Error: {e}")
            
    with tab2:
        nu = st.text_input("New User", key="sign_user")
        np = st.text_input("New Pass", type="password", key="sign_pass")
        ne = st.text_input("Email", key="sign_email")
        if st.button("Sign Up"):
            success, msg = manager.sign_up(nu, np, ne)
            if success: st.success(msg)
            else: st.error(msg)

else:
    # --- DASHBOARD ---
    # Personalize Greeting
    user_name = st.session_state.user_tab.title.replace("User_", "")
    st.sidebar.title(f"Hello {user_name}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    # Actions moved to main tabs
           
    # Test Email Button
    if st.sidebar.button("Send Test Email"):
        try:
            creds = {
                'user': st.secrets["email"]["user"],
                'password': st.secrets["email"]["password"]
            }
            success, msg = send_test_email(creds)
            if success:
                st.sidebar.success(msg)
            else:
                st.sidebar.error(f"Failed: {msg}")
        except Exception as e:
            st.sidebar.error(f"Config Error: {e}")

    # Main Area
    st.title("Portfolio Tracker")

    st.divider()

    df = load_user_transactions()
    
    if df.empty:
        st.info("Welcome! Your portfolio is empty.")
        st.markdown("### Setup Your Portfolio")
        st.write("Add your initial holdings below. These will NOT affect your cash balance.")
        
        # Initialization Editor
        # Template DF
        init_data = pd.DataFrame(columns=["Ticker", "Quantity", "Avg Cost"])
        edited_df = st.data_editor(init_data, num_rows="dynamic", key="init_editor")
        
        if st.button("Build Portfolio"):
            if not edited_df.empty:
                count = 0
                errors = []
                with st.spinner("Building Portfolio..."):
                    today = datetime.now()
                    for idx, row in edited_df.iterrows():
                        t = str(row['Ticker']).upper()
                        q = float(row['Quantity'])
                        c = float(row['Avg Cost'])
                        
                        if not t or q <= 0: continue
                        
                        # Validate Ticker
                        valid, msg = validate_ticker(t)
                        if not valid:
                            errors.append(f"Row {idx+1}: {msg}")
                            continue
                            
                        t = msg
                        # Add as 'Initial' type
                        add_user_transaction(today, t, "Initial", q, c)
                        count += 1
                
                if errors:
                    for e in errors: st.error(e)
                
                if count > 0:
                    st.success(f"Successfully added {count} positions!")
                    st.rerun()
                else:
                    st.warning("No valid positions to add.")
            else:
                st.warning("Please add some rows.")
        st.stop()
        
        st.stop()
        
    # Edit Mode Toggle
    edit_mode = st.toggle("Edit Mode")
    
    if edit_mode:
        st.markdown("### Edit Transactions")
        st.info("Edit values directly in the table below. You can also delete rows using the checkbox on the left.")
        
        # Load Raw DF for editing
        # We need to ensure types are editable
        edit_df = df.copy()
        # Ensure Date is datetime for date editor
        edit_df['Date'] = pd.to_datetime(edit_df['Date'])
        
        edited_tx = st.data_editor(
            edit_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "Ticker": st.column_config.TextColumn("Ticker", required=True),
                "Type": st.column_config.SelectboxColumn("Type", options=["Buy", "Sell", "Deposit Cash", "Withdraw Cash", "Initial"], required=True),
                "Quantity": st.column_config.NumberColumn("Quantity", min_value=0),
                "Price": st.column_config.NumberColumn("Price/Amount", min_value=0, format="$%.2f")
            },
            key="tx_editor"
        )
        
        if st.button("Save Changes"):
            if update_user_transactions(edited_tx):
                st.success("Changes saved to Google Sheets!")
                st.rerun()
                
    else:
        # Normal Dashboard View...
        pass # Flow continues to standard metrics
        
    cash = calculate_cash_balance(df)
    holdings = get_current_holdings(df)
    
    with st.spinner("Fetching data..."):
        prices = fetch_live_prices(holdings['Ticker'].unique().tolist())
        
    port_df = build_portfolio_table(holdings, prices, cash)
    metrics = calculate_portfolio_metrics(port_df, cash, df)
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", f"${metrics['total_portfolio_value']:,.2f}")
    
    # Cash Styling (Red if negative)
    cash_val = metrics['cash_balance']
    if cash_val < 0:
        c2.markdown(f"""
        <div class="stMetric">
            <label style="font-size: 14px;">Cash</label>
            <div style="font-size: 2rem; font-weight: 600; color: #ff4b4b;">${cash_val:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        c2.metric("Cash", f"${cash_val:,.2f}")

    c3.metric("Return", f"${metrics['total_return_dollars']:,.2f}", f"{metrics['total_return_pct']:.2f}%")
    c4.metric("Daily P&L", f"${metrics['daily_pnl']:,.2f}")
    
    st.divider()
    
    # --- HOLDINGS TABLE (FIXED DECIMALS) ---
    st.markdown("### Holdings")
    
    display_df = port_df.copy()
    numeric_cols = ['Avg Buy Price', 'Current Price', 'Market Value', 'Daily P&L', 'Total Return', 'Daily Return %', 'Total Return %', '% of Portfolio']
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
    
    # Conditional Formatting Function
    def color_returns(val):
        color = '#28a745' if val > 0 else '#dc3545' if val < 0 else None
        return f'color: {color}'

    st.dataframe(
        display_df.style.format({
            "Avg Buy Price": "${:,.2f}",
            "Current Price": "${:,.2f}",
            "Market Value": "${:,.2f}",
            "Daily Return %": "{:.2f}%",
            "Total Return %": "{:.2f}%",
            "% of Portfolio": "{:.2f}%",
            "Alpha vs SPY": "{:.2f}%"
        }).map(color_returns, subset=['Total Return %', 'Daily Return %']),
        column_config={
            "Qty": st.column_config.NumberColumn(format="%.4f")
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # --- MANAGE PORTFOLIO (New Location) ---
    with st.expander("Manage Portfolio (Add Transaction / Set Alert)", expanded=False):
        act_t1, act_t2 = st.tabs(["Add Transaction", "Set Alert"])
        
        with act_t1:
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
            type_ = c1.selectbox("Type", ['Buy', 'Sell', 'Deposit Cash', 'Withdraw Cash'], key="trans_type_tab")
            date_ = c2.date_input("Date", key="trans_date_tab")
            # Ensure ticker Upper
            ticker_ = c3.text_input("Ticker", key="trans_ticker_tab").upper() if type_ in ['Buy', 'Sell'] else "CASH"
            qty_ = c4.number_input("Qty", 0.0, key="trans_qty_tab") if type_ in ['Buy', 'Sell'] else 1.0
            price_ = c5.number_input("Price/Amount", 0.0, key="trans_price_tab")
            
            if st.button("Add Transaction", type="primary", key="btn_add_tab"):
                 valid_ticker = True
                 if type_ in ['Buy', 'Sell']:
                    valid, msg = validate_ticker(ticker_)
                    if not valid:
                        st.error(msg)
                        valid_ticker = False
                    else:
                        ticker_ = msg
                
                 if valid_ticker:
                    if add_user_transaction(date_, ticker_, type_, qty_, price_):
                        st.toast("Transaction Added Successfully! 🎉", icon='✅')
                        time.sleep(1)
                        st.rerun()

        with act_t2:
            c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
            at = c1.text_input("Ticker", key="alert_ticker_tab").upper()
            ap = c2.number_input("Target Price", 0.0, key="alert_price_tab")
            ac = c3.selectbox("Condition", ["Above", "Below"], key="alert_cond_tab")
            an = c4.text_input("Note", key="alert_note_tab")
            
            if st.button("Set Alert", type="primary", key="btn_set_alert_tab"):
                valid_ticker = True
                valid, msg = validate_ticker(at)
                if not valid:
                    st.error(msg)
                    valid_ticker = False
                else:
                    at = msg

                if valid_ticker:
                    if not at or not ac: st.warning("Enter Ticker/Condition")
                    elif ap < 0: st.warning("Price > 0")
                    else:
                        try:
                            with st.spinner("Saving Alert..."):
                                if add_alert_to_sheet(at, ap, ac, an):
                                    st.toast("Alert Set Successfully! 🔔", icon='✅')
                                    time.sleep(1)
                                    st.rerun()
                                else: st.error("Failed to add alert.")
                        except Exception as e: st.error(f"Error: {e}")

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
    if fig2: c2.plotly_chart(fig2, use_container_width=True)
    
    # Alerts Table
    st.markdown("### 🔔 Active Alerts")
    alerts = load_alerts()
    if not alerts.empty:
        # Loop through rows
        for i, row in alerts.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 2, 1, 1])
            c1.write(f"**{row['Ticker']}**")
            c2.write(f"${row['Target Price']}")
            c3.write(row['Direction'])
            c4.write(row['Note'])
            
            # Status
            if row['Status'] == 'Sent':
                c5.write("✅ Sent")
            else:
                c5.write("⏳ Active")
                
            # Actions
            subs_str = str(row['Subscribers'])
            subs_list = [s.strip() for s in subs_str.split(',') if s.strip()]
            user_email = st.session_state.user_email
            
            is_creator = (len(subs_list) > 0 and subs_list[0] == user_email)
            is_subscribed = (user_email in subs_list)
            
            if is_creator:
                # Reactivate if Sent
                if str(row['Status']) == 'Sent':
                    if c6.button("Reactivate", key=f"react_{i}"):
                        try:
                            with st.spinner("Reactivating..."):
                                spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
                                success, msg = reactivate_alert(spreadsheet, i)
                                if success:
                                    st.toast(msg, icon='🔄')
                                    time.sleep(1)
                                    st.rerun()
                                else: st.error(msg)
                        except Exception as e: st.error(f"Error: {e}")

                if c6.button("Delete", key=f"del_{i}"):
                    try:
                        with st.spinner("Deleting..."):
                            spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
                            success, msg = delete_alert_row(spreadsheet, i)
                            if success:
                                st.toast(msg, icon='🗑️')
                                time.sleep(1)
                                st.rerun()
                            else: st.error(msg)
                    except Exception as e: st.error(f"Error: {e}")
            elif is_subscribed:
                if c6.button("Unsubscribe", key=f"unsub_{i}"):
                    try:
                        with st.spinner("Unsubscribing..."):
                            spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
                            success, msg = unsubscribe_from_alert(spreadsheet, i, user_email)
                            if success:
                                st.toast(msg, icon='👋')
                                time.sleep(1)
                                st.rerun()
                            else: st.error(msg)
                    except Exception as e: st.error(f"Error: {e}")
            else:
                 if c6.button("Join", key=f"join_{i}"):
                    try:
                        with st.spinner("Joining..."):
                            spreadsheet = manager.client.open_by_key(manager.USERS_DB_ID)
                            success, msg = subscribe_to_alert(spreadsheet, i, user_email)
                            if success:
                                st.toast(msg, icon='✅')
                                time.sleep(1)
                                st.rerun()
                            else: st.error(msg)
                    except Exception as e: st.error(f"Error: {e}")
    else:
        st.info("No active alerts.")
