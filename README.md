# 📈 Pro Portfolio Tracker

A **100% free**, production-grade personal portfolio management application with real-time stock data, performance analytics, and automated price alerts.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎯 Portfolio Management
- **Real-time stock prices** via Yahoo Finance API
- **Cash tracking** with automatic updates on trades
- **Transaction history** stored in Google Sheets
- **Buy/Sell functionality** directly from the dashboard

### 📊 Advanced Analytics
- **Performance metrics**: Total return, daily P&L, portfolio value
- **Benchmark comparison**: Alpha vs S&P 500 for each holding
- **Historical performance charts**: Compare your returns against SPY
- **Multiple timeframes**: 1W, 1M, YTD, 1Y, All-time
- **Sector allocation**: Automatic sector breakdown from yfinance

### 🔔 Price Alerts
- **Automated monitoring** via GitHub Actions
- **Email notifications** when price targets are hit
- **Customizable conditions**: Above/Below target price
- **Runs during market hours** automatically

### 💰 Zero Cost
- **Free hosting** on Streamlit Cloud
- **Free database** using Google Sheets
- **Free automation** with GitHub Actions
- **No credit card required** for any component

---

## 🚀 Quick Start

1. **Clone this repository**
   ```bash
   git clone https://github.com/yourusername/pro-portfolio-tracker.git
   cd pro-portfolio-tracker
   ```

2. **Follow the setup guide**
   - See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions

3. **Deploy to Streamlit Cloud**
   - Connect your GitHub repo
   - Add secrets
   - Deploy (takes 2 minutes!)

---

## 📸 Screenshots

### Portfolio Dashboard
![Dashboard](https://via.placeholder.com/800x400?text=Portfolio+Dashboard)

### Historical Performance
![Performance Chart](https://via.placeholder.com/800x400?text=Performance+Chart)

### Holdings Table
![Holdings](https://via.placeholder.com/800x400?text=Holdings+Table)

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Interactive web dashboard |
| **Charts** | Plotly | Beautiful, interactive visualizations |
| **Data** | yfinance | Real-time stock prices |
| **Database** | Google Sheets | Transaction & alert storage |
| **Automation** | GitHub Actions | Scheduled price alerts |
| **Email** | Gmail SMTP | Alert notifications |

---

## 📋 Project Structure

```
pro-portfolio-tracker/
├── app.py                          # Main Streamlit dashboard
├── portfolio_logic.py              # Business logic & calculations
├── alerts.py                       # Price alert checker
├── requirements.txt                # Python dependencies
├── SETUP_GUIDE.md                  # Detailed setup instructions
├── .github/
│   └── workflows/
│       └── alerts.yml              # GitHub Actions workflow
├── .env.example                    # Environment variables template
└── .gitignore                      # Git ignore rules
```

---

## 📊 Portfolio Metrics Explained

### Main Table Columns

| Column | Description |
|--------|-------------|
| **Ticker** | Stock symbol |
| **Qty** | Number of shares owned |
| **Avg Buy Price** | Average purchase price per share |
| **Current Price** | Live market price |
| **Market Value** | Current value of position |
| **% of Portfolio** | Position size as % of total portfolio |
| **Total Return %** | Return since purchase |
| **Daily Return %** | Today's performance |
| **Alpha vs SPY** | Outperformance vs S&P 500 since purchase |

### KPI Metrics

- **Total Portfolio Value**: Sum of all holdings + cash
- **Cash Balance**: Current available cash
- **Total Return**: Profit/loss in dollars and percentage
- **Daily P&L**: Today's profit/loss

---

## 🔐 Security & Privacy

- ✅ **Your data stays in your Google Sheet** - we never store it elsewhere
- ✅ **Service account credentials** are securely stored in Streamlit secrets
- ✅ **GitHub secrets** are encrypted and never exposed in logs
- ✅ **No third-party data sharing** - everything runs on free platforms

---

## 🎓 Use Cases

Perfect for:
- 📈 **Individual investors** tracking their brokerage accounts
- 💼 **Side portfolios** separate from main brokerage
- 🎓 **Paper trading** for learning without real money
- 📊 **Portfolio analysis** with better metrics than broker apps
- 🔍 **Comparing strategies** across different accounts

---

## 🐛 Known Limitations

- **Market data delay**: Yahoo Finance has ~15-minute delay for some stocks
- **No automatic sync**: Must manually enter transactions (no broker integration)
- **GitHub Actions quota**: 2,000 minutes/month (more than enough for hourly checks)
- **Email limits**: Gmail allows 500 emails/day (way more than you'll need)

---

## 🚧 Roadmap

Future enhancements:
- [ ] Multi-currency support
- [ ] Dividend tracking & reinvestment
- [ ] Tax loss harvesting suggestions
- [ ] Portfolio rebalancing recommendations
- [ ] Options & crypto support
- [ ] Mobile app version
- [ ] Broker API integration (Alpaca, Interactive Brokers)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 💬 Support

Having issues? Check:
1. [Setup Guide](SETUP_GUIDE.md) - detailed instructions
2. [Issues](https://github.com/yourusername/pro-portfolio-tracker/issues) - known problems
3. Create a new issue with details about your problem

---

## 🌟 Show Your Support

If this project helped you, please give it a ⭐️!

---

**Built with ❤️ for the DIY investor community**
