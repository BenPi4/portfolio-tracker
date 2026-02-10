# Pro Portfolio Tracker - Setup Guide

A 100% free, production-grade portfolio management application with real-time data, historical analysis, and automated price alerts.

## 🎯 Features

- **Real-time Portfolio Tracking**: Live stock prices via yfinance
- **Performance Analytics**: Compare your returns vs S&P 500
- **Interactive Dashboard**: Streamlit-based UI with Plotly charts
- **Price Alerts**: Automated email notifications via GitHub Actions
- **Zero Cost**: Completely free to host and run

---

## 📋 Prerequisites

1. **Google Account** (for Google Sheets database)
2. **GitHub Account** (for hosting and automation)
3. **Gmail Account** (for sending alert emails)

---

## 🚀 Setup Instructions

### Step 1: Google Sheets Setup

1. **Create a new Google Sheet** named "Portfolio Tracker"

2. **Create two tabs:**

   **Tab 1: Transactions**
   - Column A: `Date` (format: YYYY-MM-DD)
   - Column B: `Ticker` (e.g., AAPL, MSFT)
   - Column C: `Type` (Buy, Sell, Deposit Cash, Withdraw Cash)
   - Column D: `Quantity` (number of shares)
   - Column E: `Price` (price per share or amount for cash transactions)

   **Tab 2: Alerts**
   - Column A: `Ticker`
   - Column B: `Target_Price`
   - Column C: `Condition` (Above or Below)
   - Column D: `Email_Sent` (True or False)

3. **Add some sample data** to test:
   ```
   Transactions tab:
   Date        | Ticker | Type        | Quantity | Price
   2024-01-15  | VOO    | Buy         | 10       | 450.00
   2024-01-15  | CASH   | Deposit Cash| 1        | 10000.00
   
   Alerts tab:
   Ticker | Target_Price | Condition | Email_Sent
   AAPL   | 200          | Above     | False
   ```

---

### Step 2: Google Cloud API Setup

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create a new project**:
   - Click "Select a project" → "New Project"
   - Name: "Portfolio Tracker"
   - Click "Create"

3. **Enable Google Sheets API**:
   - In the search bar, type "Google Sheets API"
   - Click "Enable"

4. **Enable Google Drive API**:
   - Search for "Google Drive API"
   - Click "Enable"

5. **Create Service Account**:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Name: "portfolio-tracker"
   - Click "Create and Continue"
   - Skip role assignment (click "Continue")
   - Click "Done"

6. **Create Service Account Key**:
   - Click on your newly created service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Click "Create" - a JSON file will download
   - **Keep this file safe!** This is your `credentials.json`

7. **Share Google Sheet with Service Account**:
   - Open your Google Sheet
   - Click "Share"
   - Copy the service account email from the JSON file (looks like: `portfolio-tracker@xxx.iam.gserviceaccount.com`)
   - Paste it in the "Add people" field
   - Give "Editor" access
   - Uncheck "Notify people"
   - Click "Share"

---

### Step 3: Gmail App Password Setup

1. **Enable 2-Step Verification**:
   - Go to https://myaccount.google.com/security
   - Under "Signing in to Google", enable "2-Step Verification"

2. **Create App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other (Custom name)" → Type "Portfolio Tracker"
   - Click "Generate"
   - **Save the 16-character password** - you'll need this for alerts

---

### Step 4: Deploy to Streamlit Cloud (Free)

1. **Fork this repository** to your GitHub account

2. **Go to Streamlit Cloud**: https://share.streamlit.io/

3. **Sign in with GitHub**

4. **Click "New app"**

5. **Configure deployment**:
   - Repository: Select your forked repo
   - Branch: main
   - Main file path: `app.py`

6. **Add Secrets** (Click "Advanced settings" → "Secrets"):

   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYour-Key-Here\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-cert-url"
   ```

   **How to get these values**: Copy them from the JSON file you downloaded in Step 2.6

7. **Add environment variable**:
   ```toml
   GOOGLE_SHEET_NAME = "Portfolio Tracker"
   ```

8. **Click "Deploy"** - Your app will be live in 2-3 minutes!

---

### Step 5: GitHub Actions Setup (for Alerts)

1. **Go to your GitHub repository**

2. **Click "Settings" → "Secrets and variables" → "Actions"**

3. **Add the following secrets** (Click "New repository secret"):

   - **GOOGLE_CREDENTIALS**: 
     - Paste the **entire contents** of your `credentials.json` file
     - It should be a single line of JSON
   
   - **GOOGLE_SHEET_NAME**: 
     - Value: `Portfolio Tracker`
   
   - **GMAIL_SENDER**: 
     - Your Gmail address (e.g., `yourname@gmail.com`)
   
   - **GMAIL_APP_PASSWORD**: 
     - The 16-character app password from Step 3
   
   - **ALERT_EMAIL**: 
     - Email where you want to receive alerts (can be the same as GMAIL_SENDER)

4. **Enable GitHub Actions**:
   - Go to "Actions" tab in your repo
   - If needed, click "I understand my workflows, go ahead and enable them"

5. **Test the workflow**:
   - Go to "Actions" tab
   - Click "Price Alerts Checker"
   - Click "Run workflow" → "Run workflow"
   - Check the logs to ensure it works

---

## 📱 Using the App

### Adding Transactions

1. **Open the sidebar** in your Streamlit app
2. **Click "Add Transaction"**
3. **Select transaction type**:
   - **Buy**: Purchase stocks (decreases cash)
   - **Sell**: Sell stocks (increases cash)
   - **Deposit Cash**: Add cash to portfolio
   - **Withdraw Cash**: Remove cash from portfolio
4. **Fill in the details** and click "Add Transaction"

### Setting Price Alerts

1. **In the sidebar**, click "Set Price Alert"
2. **Enter ticker symbol** (e.g., AAPL)
3. **Set target price**
4. **Choose condition**: Above or Below
5. **Click "Create Alert"**

The system will check prices every hour during market hours and email you when conditions are met.

### Viewing Analytics

- **Portfolio Overview**: Top metrics showing total value, cash, returns, and daily P&L
- **Holdings Table**: Detailed view of each position with performance metrics
- **Historical Performance**: Chart comparing your portfolio vs S&P 500
- **Allocation Charts**: Pie charts showing holdings and sector distribution

---

## 🎨 Customization

### Changing Alert Frequency

Edit `.github/workflows/alerts.yml`:

```yaml
schedule:
  # Check every 30 minutes during market hours
  - cron: '*/30 14-21 * * 1-5'
```

### Adding More Metrics

Edit `portfolio_logic.py` to add custom calculations, then display them in `app.py`.

### Styling

Modify the CSS in `app.py` under `st.markdown()` sections.

---

## 🐛 Troubleshooting

### "Error connecting to Google Sheets"
- Verify service account email has Editor access to your sheet
- Check that all credentials are correctly copied to Streamlit secrets
- Ensure Google Sheets API and Drive API are enabled

### "Error fetching price data"
- Some stocks may not be available on Yahoo Finance
- Check ticker symbol is correct
- Try again later (API may be rate-limiting)

### Alerts not sending emails
- Verify Gmail app password is correct (16 characters, no spaces)
- Check GitHub Actions logs for specific errors
- Ensure 2-Step Verification is enabled on Gmail

### App is slow
- Reduce the number of holdings
- Increase cache TTL in `app.py` (currently 5 minutes)

---

## 💡 Tips

1. **Regular backups**: Download your Google Sheet periodically
2. **Test alerts**: Set a low price alert to test the system
3. **Monitor costs**: This setup is 100% free, but be aware of any potential quotas
4. **Privacy**: Your data stays in your Google Sheet - we never store it elsewhere

---

## 📊 Sample Portfolio

To quickly test the app, add these sample transactions:

```csv
Date,Ticker,Type,Quantity,Price
2024-01-01,CASH,Deposit Cash,1,50000
2024-01-15,VOO,Buy,50,450.00
2024-01-20,QQQ,Buy,40,380.00
2024-02-01,NVDA,Buy,25,480.00
2024-02-10,AMZN,Buy,60,175.00
```

---

## 🚀 Advanced Features (Future Enhancements)

- Multi-currency support
- Dividend tracking
- Tax loss harvesting suggestions
- Portfolio rebalancing recommendations
- Integration with broker APIs

---

## 📝 License

This project is open-source and free to use for personal portfolio management.

---

## 🤝 Support

If you encounter issues:
1. Check this guide first
2. Review GitHub Actions logs
3. Verify all secrets are set correctly
4. Check Google Sheet permissions

---

**Happy Investing! 📈**
