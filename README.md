# 📈 Opening Range Breakout (ORB) Trading Bot

A complete local Python application that runs an Opening Range Breakout (ORB) trading strategy using Angel One SmartAPI with a Streamlit dashboard.

## 🎯 Strategy Overview

The Opening Range Breakout (ORB) strategy is a popular intraday trading strategy that:

1. **Builds an opening range** from 9:15 AM to 11:15 AM IST
2. **Tracks the High and Low** of this range
3. **Enters LONG** when price breaks above the range high
4. **Enters SHORT** when price breaks below the range low
5. **Exits at 3:20 PM** regardless of profit/loss
6. **Takes only ONE trade per day**

### Target Stock
- **Symbol:** RELIANCE-EQ
- **Exchange:** NSE (National Stock Exchange of India)
- **Position Size:** 1 share

## 📁 Project Structure

```
AlgoTrading/
├── app.py                    # Main Streamlit application
├── strategy/
│   ├── __init__.py
│   └── orb_strategy.py       # ORB strategy implementation
├── broker/
│   ├── __init__.py
│   └── angel_client.py       # Angel One SmartAPI wrapper
├── utils/
│   ├── __init__.py
│   └── time_utils.py         # Time utilities for IST
├── logs/
│   └── trades.csv            # Trade log file
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
├── .env                      # Your credentials (create this)
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Angel One Trading Account
- Angel One SmartAPI credentials

### 1. Clone/Setup the Project

```bash
cd AlgoTrading
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

Create a `.env` file from the example:

```bash
copy .env.example .env
```

Edit the `.env` file with your Angel One credentials:

```env
ANGEL_API_KEY=your_api_key_here
ANGEL_CLIENT_ID=your_client_id_here
ANGEL_PASSWORD=your_password_here
ANGEL_TOTP=your_totp_secret_here
```

#### Getting Your Credentials

1. **API Key:** Sign up at [Angel One SmartAPI](https://smartapi.angelone.in/) and create an app
2. **Client ID:** Your Angel One trading account ID
3. **Password:** Your trading password or MPIN
4. **TOTP Secret:** The secret key from your 2FA setup (used to generate TOTP codes)

### 5. Run the Application

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## 💡 Features

### Dashboard (Streamlit UI)

- **Current Price:** Real-time LTP from Angel One
- **Opening Range:** High and Low of the opening range
- **Strategy State:** Current state of the strategy
- **Position Status:** Current position (LONG/SHORT/NONE)
- **Entry Price:** Price at which position was entered
- **Unrealized PnL:** Current profit/loss on open position
- **Trade Log:** History of all trades

### Controls

- **Start Bot:** Begin automated trading
- **Stop Bot:** Stop automated trading
- **Paper Trading Toggle:** Switch between paper and live trading
- **Reconnect:** Manually reconnect to the broker

### Market Hours Control

The strategy only operates during market hours:
- **Market Open:** 9:15 AM IST
- **Range Building:** 9:15 AM - 11:15 AM IST
- **Trading Period:** 11:15 AM - 3:20 PM IST
- **Exit Time:** 3:20 PM IST
- **Market Close:** 3:30 PM IST

### Trading Logs

All trades are logged to `logs/trades.csv` with:
- Timestamp
- Action (BUY/SELL/EXIT_LONG/EXIT_SHORT)
- Price
- Quantity
- Position Type
- PnL
- Order ID

## 🔧 Configuration

### Strategy Parameters

Edit these in `strategy/orb_strategy.py`:

```python
POSITION_SIZE = 1  # Number of shares per trade
```

### Symbol Configuration

Edit the symbol in `broker/angel_client.py`:

```python
RELIANCE_CONFIG = {
    'exchange': 'NSE',
    'tradingsymbol': 'RELIANCE-EQ',
    'symboltoken': '2885',
}
```

### Time Settings

Edit timings in `utils/time_utils.py`:

```python
MARKET_OPEN = time(9, 15)   # 9:15 AM
RANGE_END = time(11, 15)    # 11:15 AM
EXIT_TIME = time(15, 20)    # 3:20 PM
MARKET_CLOSE = time(15, 30) # 3:30 PM
```

## 🔄 Switching to Live Trading

1. In the Streamlit sidebar, **uncheck** "Paper Trading Mode"
2. Or modify the code to default to live trading:

```python
# In app.py
st.session_state.broker = AngelOneClient(paper_trading=False)
```

⚠️ **WARNING:** Live trading uses real money. Test thoroughly in paper mode first!

## 📊 Strategy Flow

```
┌─────────────────────────────────────────────────────────┐
│                    MARKET OPENS (9:15 AM)                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              BUILDING RANGE (9:15 - 11:15 AM)            │
│         Track highest high and lowest low                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              RANGE COMPLETE (11:15 AM)                   │
│         Range High and Range Low are set                 │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│            WAITING FOR BREAKOUT (11:15 - 3:20 PM)        │
│                                                          │
│    Price >= Range High  ──────────►  ENTER LONG          │
│    Price <= Range Low   ──────────►  ENTER SHORT         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│               EXIT TIME (3:20 PM)                        │
│         Close all open positions                         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              MARKET CLOSES (3:30 PM)                     │
│         Reset for next trading day                       │
└─────────────────────────────────────────────────────────┘
```

## ⚠️ Error Handling

The system handles:
- **API Failures:** Automatic retry and reconnection
- **Internet Disconnect:** Graceful handling with error messages
- **Market Closed:** Prevents trading outside market hours
- **Session Expiry:** Automatic token refresh/relogin

## 🔐 Security

- Credentials are stored in `.env` file (not committed to git)
- Add `.env` to your `.gitignore`
- Never hardcode credentials in the source code

## 📝 Logging

- Console logging for real-time debugging
- Trade log saved to `logs/trades.csv`
- All timestamps in IST (Asia/Kolkata)

## 🛠️ Troubleshooting

### "Failed to connect to broker"
- Check your `.env` credentials
- Ensure your TOTP secret is correct
- Verify your Angel One account is active

### "Failed to fetch LTP"
- Check internet connection
- Verify the symbol token is correct
- Ensure market is open

### "Token expired"
- The system will auto-reconnect
- Click "Reconnect" button if needed

## 📈 Future Enhancements

- [ ] Add stop-loss functionality
- [ ] Support multiple stocks
- [ ] Real-time WebSocket data feed
- [ ] Position sizing based on risk
- [ ] Backtesting module
- [ ] Email/SMS notifications
- [ ] Historical performance analytics

## 📄 License

This project is for educational purposes. Use at your own risk.

## 🤝 Disclaimer

**IMPORTANT:** This software is provided for educational purposes only. Trading in the stock market involves substantial risk of loss. Past performance is not indicative of future results. The authors are not responsible for any financial losses incurred through the use of this software. Always do your own research and consult with a qualified financial advisor before trading.
