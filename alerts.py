"""
Price Alerts System - Standalone script for GitHub Actions
Checks price conditions and sends email notifications via Gmail SMTP.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime


def get_sheets_client():
    """Initialize Google Sheets client from environment credentials."""
    try:
        credentials_json = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json:
            print("ERROR: GOOGLE_CREDENTIALS not found in environment")
            return None
        
        credentials_dict = json.loads(credentials_json)
        
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
        print(f"ERROR initializing Google Sheets: {e}")
        return None


def fetch_current_price(ticker):
    """Fetch current price for a ticker using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None:
            hist = stock.history(period='1d')
            if len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
        
        return current_price
    except Exception as e:
        print(f"ERROR fetching price for {ticker}: {e}")
        return None


def send_email_alert(ticker, current_price, target_price, condition):
    """Send email notification via Gmail SMTP."""
    try:
        # Email configuration from environment
        sender_email = os.getenv('GMAIL_SENDER')
        sender_password = os.getenv('GMAIL_APP_PASSWORD')
        recipient_email = os.getenv('ALERT_EMAIL')
        
        if not all([sender_email, sender_password, recipient_email]):
            print("ERROR: Email credentials not fully configured")
            return False
        
        # Create message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = f"🔔 Price Alert: {ticker} ${current_price:.2f}"
        
        # Email body
        body = f"""
Portfolio Price Alert Triggered!

Ticker: {ticker}
Current Price: ${current_price:.2f}
Target Price: ${target_price:.2f}
Condition: {condition}

The price is now {condition.lower()} your target.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Pro Portfolio Tracker
        """
        
        message.attach(MIMEText(body, 'plain'))
        
        # Send email via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print(f"✅ Email sent for {ticker}")
        return True
        
    except Exception as e:
        print(f"ERROR sending email: {e}")
        return False


def update_alert_status(worksheet, row_index):
    """Update Email_Sent status to True in the sheet."""
    try:
        # Column D is Email_Sent (index 4)
        worksheet.update_cell(row_index, 4, 'True')
        print(f"✅ Updated alert status for row {row_index}")
        return True
    except Exception as e:
        print(f"ERROR updating alert status: {e}")
        return False


def check_alerts():
    """Main function to check all active alerts."""
    print(f"🔍 Starting alert check at {datetime.now()}")
    
    # Get Google Sheets client
    client = get_sheets_client()
    if not client:
        print("❌ Failed to initialize Google Sheets client")
        return
    
    # Get sheet name
    sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Portfolio Tracker')
    
    try:
        # Open spreadsheet and alerts worksheet
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet('Alerts')
        
        # Get all alerts
        alerts = worksheet.get_all_records()
        
        if not alerts:
            print("ℹ️ No alerts found")
            return
        
        print(f"📋 Found {len(alerts)} total alerts")
        
        # Process each alert
        alerts_triggered = 0
        
        for idx, alert in enumerate(alerts, start=2):  # Start at 2 (row 1 is header)
            # Skip if already sent
            if alert.get('Email_Sent') == 'True':
                continue
            
            ticker = alert.get('Ticker', '').strip()
            target_price = float(alert.get('Target_Price', 0))
            condition = alert.get('Condition', '').strip()
            
            if not ticker or not target_price:
                print(f"⚠️ Skipping invalid alert in row {idx}")
                continue
            
            print(f"Checking {ticker}: Target ${target_price} ({condition})")
            
            # Fetch current price
            current_price = fetch_current_price(ticker)
            
            if current_price is None:
                print(f"⚠️ Could not fetch price for {ticker}")
                continue
            
            print(f"  Current price: ${current_price:.2f}")
            
            # Check condition
            alert_triggered = False
            
            if condition == 'Above' and current_price >= target_price:
                alert_triggered = True
                print(f"  🔔 ALERT! Price is above target")
            elif condition == 'Below' and current_price <= target_price:
                alert_triggered = True
                print(f"  🔔 ALERT! Price is below target")
            
            # Send email and update status if triggered
            if alert_triggered:
                if send_email_alert(ticker, current_price, target_price, condition):
                    update_alert_status(worksheet, idx)
                    alerts_triggered += 1
        
        print(f"\n✅ Alert check complete. {alerts_triggered} alert(s) triggered.")
        
    except Exception as e:
        print(f"❌ ERROR in check_alerts: {e}")


if __name__ == "__main__":
    check_alerts()
