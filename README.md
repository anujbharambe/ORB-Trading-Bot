# AlgoTrading — Opening Range Breakout Bot

A real-time **Opening Range Breakout (ORB)** trading bot for NSE stocks, integrated with **Angel One SmartAPI**. Includes a live trading dashboard (Streamlit) and a comprehensive backtesting engine with analytics.

## Strategy

1. **9:15 AM – 11:15 AM IST** — Builds the opening range by tracking the high and low during this window.
2. **11:15 AM – 3:20 PM IST** — Trades breakouts:
   - **LONG** if price breaks above the range high.
   - **SHORT** if price breaks below the range low.
3. **Exit** — At 3:20 PM (end of day) or when the stop-loss (opposite side of the opening range) is hit.
4. **Risk** — One trade per day by default (configurable).

## Project Structure

```
app.py                  # Streamlit live trading dashboard
config.yaml             # All strategy, risk & broker settings
broker/angel_client.py  # Angel One SmartAPI integration
strategy/orb_strategy.py# ORB strategy logic
strategy/bot_runner.py  # Background bot thread manager
utils/config.py         # Loads config.yaml
utils/time_utils.py     # IST timezone & market hour helpers
backtesting/            # Backtesting engine, analytics & Streamlit UI
data/                   # Historical 5-minute candle CSVs
```

## Setup

### Prerequisites

- Python 3.10+
- An Angel One trading account with API access

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd AlgoTrading

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root with your Angel One credentials:

```
ANGEL_API_KEY=<your_api_key>
ANGEL_CLIENT_ID=<your_client_id>
ANGEL_PASSWORD=<your_password>
ANGEL_TOTP=<your_totp_secret>
```

All four are required for live trading.

### Configuration

Edit `config.yaml` to adjust:

| Section | Key | Description |
|---|---|---|
| **symbol** | `tradingsymbol`, `symboltoken` | Instrument to trade (default: RELIANCE-EQ) |
| **position_sizing** | `mode`, `fixed_quantity`, `capital`, `leverage` | How trade size is determined |
| **market_timings** | `range_end`, `exit_time` | Opening range window & forced exit time |
| **risk** | `stop_loss_enabled`, `max_daily_trades` | Stop-loss toggle & daily trade cap |
| **bot** | `tick_interval`, `retry_delays` | Polling frequency & reconnection backoff |

## Usage

### Live Trading Dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Use the sidebar to toggle paper/live mode and start or stop the bot.

### Backtesting (CLI)

```bash
# Default backtest
python -m backtesting

# Custom parameters
python -m backtesting --symbol RELIANCE-EQ --start 2020-01-01 --end 2024-12-31 --capital 500000 --leverage 3
```

Results are saved to `backtesting_results/`.

### Backtesting (Streamlit UI)

```bash
streamlit run backtesting/app.py
```

Interactive dashboard with equity curves, drawdown charts, monthly/yearly heatmaps, and downloadable results.

## Dependencies

Key packages (see `requirements.txt` for full list):

- **smartapi-python** — Angel One broker API
- **streamlit** — Web dashboard
- **pandas / numpy** — Data processing
- **matplotlib / plotly** — Charting
- **python-dotenv** — Credential management
- **pyotp** — TOTP 2FA generation
