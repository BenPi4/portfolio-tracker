# 📈 Pro Portfolio Tracker

**Full-Stack Investment Portfolio Management Application**

A production-ready web application built with Python, Streamlit, and Google Cloud Platform for real-time portfolio tracking, financial analytics, and automated monitoring. Features interactive data visualizations, cloud database integration, and serverless automation.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🎯 Project Overview

This application demonstrates full-stack development skills including:
- **Backend Development**: Python-based business logic with modular architecture
- **Frontend Development**: Interactive dashboard with responsive UI using Streamlit
- **Cloud Integration**: Google Sheets API for cloud database management
- **Data Visualization**: Dynamic charts using Plotly for financial analytics
- **API Integration**: Real-time market data fetching via yfinance
- **DevOps**: CI/CD with GitHub Actions for automated monitoring
- **Authentication**: Multi-user system with secure credential management

**Technical Highlights for Interviewers:**
- Clean separation of concerns (MVC-inspired architecture)
- RESTful API interaction patterns
- OAuth 2.0 service account authentication
- Asynchronous data processing
- Error handling and input validation
- Production deployment on cloud platform

---

## 🛠️ Technical Stack

### Core Technologies
- **Python 3.14** - Primary programming language
- **Streamlit** - Web framework for interactive dashboards
- **Pandas** - Data manipulation and analysis
- **Plotly** - Interactive data visualization library
- **yfinance** - Financial market data API

### Cloud & DevOps
- **Google Cloud Platform (GCP)** - Cloud infrastructure
  - Google Sheets API for database
  - Service Account authentication
- **GitHub Actions** - CI/CD automation
- **Streamlit Cloud** - Application hosting

### Key Libraries
```python
streamlit          # Web framework
pandas             # Data processing
plotly             # Visualizations
yfinance           # Market data
gspread            # Google Sheets integration
google-oauth2      # Authentication
```

---

## ✨ Key Features & Technical Implementation

### 1. Real-Time Portfolio Management
- **Multi-user authentication system** with secure credential storage
- **Transaction tracking** (Buy/Sell/Deposit/Withdraw)
- **Live market data** integration via Yahoo Finance API
- **Automatic cash balance** calculation with transaction reconciliation

**Technical Skills Demonstrated:**
- API integration and data fetching
- Database CRUD operations
- User session management
- Financial calculations and reconciliation

### 2. Advanced Financial Analytics

#### Performance Metrics
- **Portfolio returns** with time-weighted calculations
- **Benchmark comparison** (Alpha vs S&P 500)
- **Daily P&L** with intraday performance tracking
- **Asset allocation** analysis with percentage calculations

#### Interactive Visualizations
- **Historical performance charts** with multiple timeframes (1W, 1M, YTD, 1Y, All-time)
- **Donut charts** for holdings and sector allocation with Top 6 + Other grouping
- **Responsive design** with customizable layouts

**Technical Skills Demonstrated:**
- Complex financial calculations
- Data aggregation and transformation
- Statistical analysis
- Interactive chart creation with Plotly
- UI/UX optimization (clutter reduction, smart labeling)

### 3. Cloud Database Integration
- **Google Sheets as database** using gspread library
- **Service account authentication** with GCP credentials
- **Multi-sheet architecture** for users and alerts
- **Real-time data sync** between app and database

**Technical Skills Demonstrated:**
- Cloud API integration (Google Sheets API)
- OAuth 2.0 authentication flow
- Credential management with secrets
- Data persistence and retrieval

### 4. Automated Price Alerts
- **GitHub Actions workflow** for scheduled monitoring
- **Email notifications** via SMTP
- **Configurable alerts** (Above/Below conditions)
- **Market hours scheduling** for optimal execution

**Technical Skills Demonstrated:**
- CI/CD pipeline configuration
- Scheduled task automation
- Email integration
- Conditional logic and monitoring

### 5. Code Architecture

**Modular Design:**
```
portfolio-tracker/
├── app.py                 # Main application & UI layer
├── portfolio_logic.py     # Business logic & calculations
├── manager.py             # Authentication & database management
├── alerts.py              # Alert monitoring system
└── .github/workflows/     # CI/CD automation
```

**Design Patterns:**
- Separation of concerns (UI, Logic, Data)
- Reusable functions and components
- Error handling with try-except blocks
- Configuration management with environment variables

---

## 🎓 Technical Challenges Solved

### 1. Negative Cash Handling
**Problem**: Portfolio percentages showed > 100% when using margin (negative cash)  
**Solution**: Modified allocation calculation to use `max(0, cash_balance)` for total assets

### 2. Chart Clutter Reduction
**Problem**: Too many small positions made pie charts unreadable  
**Solution**: Implemented "Top 6 + Other" aggregation logic with dynamic filtering

### 3. API Rate Limiting
**Problem**: Individual stock API calls caused rate limiting  
**Solution**: Bulk data downloads using yfinance with 5-day history caching

### 4. Decimal Precision
**Problem**: Floating-point calculations showed excessive decimals  
**Solution**: Custom formatting with Streamlit `column_config` and Plotly `texttemplate`

### 5. Multi-User Authentication
**Problem**: Secure credential storage without exposing sensitive data  
**Solution**: Streamlit secrets + local file fallback with try-except error handling

---

## 📊 Key Metrics & Calculations

**Financial Formulas Implemented:**
```python
# Portfolio Return %
return_pct = ((current_value - invested_capital) / invested_capital) * 100

# Alpha vs S&P 500
alpha = portfolio_return - spy_return

# Daily P&L
daily_pnl = sum(position_value * daily_return_pct / 100)

# Asset Allocation %
allocation = (position_value / total_assets) * 100
```

---

## 🚀 Deployment & DevOps

### Continuous Integration
- GitHub Actions workflow for automated alerts
- Scheduled execution during market hours (9:30 AM - 4:00 PM EST)
- Environment variable management
- Email notifications on alert triggers

### Cloud Deployment
- One-click deployment to Streamlit Cloud
- Secret management via Streamlit secrets
- Automatic dependency resolution from `requirements.txt`
- Zero downtime updates with version control

---

## 💡 Skills Demonstrated

### Programming & Development
- ✅ Python (Advanced)
- ✅ API Integration
- ✅ Data Structures & Algorithms
- ✅ Object-Oriented Programming
- ✅ Error Handling & Debugging

### Data & Analytics
- ✅ Pandas for data manipulation
- ✅ Financial calculations
- ✅ Data visualization (Plotly)
- ✅ Statistical analysis

### Cloud & DevOps
- ✅ Google Cloud Platform (GCP)
- ✅ CI/CD with GitHub Actions
- ✅ OAuth 2.0 authentication
- ✅ Cloud deployment (Streamlit Cloud)
- ✅ Secret management

### Software Engineering
- ✅ Modular architecture
- ✅ Code documentation
- ✅ Version control (Git)
- ✅ RESTful API design patterns
- ✅ Testing & validation

### Product Development
- ✅ User authentication system
- ✅ Multi-user support
- ✅ UI/UX design
- ✅ Responsive layouts

---

## 🔧 Setup & Installation

### Prerequisites
```bash
Python 3.8+
Google Cloud Platform account (free)
GitHub account (free)
```

### Local Development
```bash
# 1. Clone repository
git clone https://github.com/BenPi4/portfolio-tracker.git
cd portfolio-tracker

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add credentials.json (GCP service account)
# Place your credentials.json in the root directory

# 5. Run application
streamlit run app.py
```

### Production Deployment
1. Fork this repository
2. Connect to Streamlit Cloud
3. Add `gcp_service_account` secret
4. Deploy automatically

---

## 📈 Future Enhancements

**Planned Features:**
- [ ] Broker API integration (Alpaca, Interactive Brokers)
- [ ] Dividend tracking & reinvestment calculations
- [ ] Tax loss harvesting recommendations
- [ ] Multi-currency support
- [ ] Options & crypto portfolio tracking
- [ ] Mobile-responsive PWA version
- [ ] Portfolio rebalancing optimizer
- [ ] Risk analysis (Sharpe ratio, beta, volatility)

---

## 📄 License

MIT License - feel free to use this project as a reference or starting point for your own applications.

---

## 👨‍💻 About This Project

This project showcases my ability to:
- Build production-ready applications from scratch
- Integrate multiple technologies and APIs
- Solve complex technical challenges
- Write clean, maintainable code
- Deploy and maintain cloud applications

**Perfect for demonstrating to potential employers:**
- Full-stack development capabilities
- Cloud platform experience
- Financial domain knowledge
- Problem-solving skills
- Production deployment experience

---

**Built by Ben Pitkovsky** | [LinkedIn](https://linkedin.com/in/yourprofile) | [Portfolio](https://yourportfolio.com)
