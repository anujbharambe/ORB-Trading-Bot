# 🛣️ Roadmap — Planned Improvements & Features

> **Note:** These are planned enhancements and have **not been implemented yet**. They are listed here for future reference and prioritization.

---

## Phase 1: Configuration & Flexibility
- [x] **Configurable symbol/instrument** — Move RELIANCE-EQ config (symbol, exchange, token) out of hardcoded `angel_client.py` into `.env` or a `config.yaml`. Allow trading any NSE/BSE instrument without code changes.
- [x] **Configurable position sizing** — Currently hardcoded to 1 share. Support fixed quantity, fixed capital amount, or percentage-of-capital modes via config.
- [x] **Centralized configuration** — Tick interval (5s), health check interval (60s), retry delays, and market timings are scattered as hardcoded constants. Centralize all tunable parameters in one config file.

## Phase 2: Risk Management Infrastructure
- [ ] **Stop-loss / trailing stop-loss** — No stop-loss exists. Add configurable stop-loss (fixed points, percentage, or ATR-based) as a risk management layer independent of strategy logic.
- [ ] **Max daily loss limit** — If cumulative daily PnL breaches a configurable threshold, auto-stop the bot for the day.
- [ ] **Capital tracking & position limits** — Track available capital, prevent over-leveraging, enforce max position value.

## Phase 3: Real-time Data via WebSocket
- [ ] **WebSocket price streaming** — `websocket-client` is already a dependency but unused. Replace the 5-second LTP polling with Angel One's WebSocket feed for real-time tick data. Reduces latency and API call overhead.

## Phase 4: Notifications & Alerting
- [ ] **Trade notifications** — Send alerts on trade entry/exit/errors via Telegram bot, email (SMTP), or Discord webhook. Currently all feedback is only visible in the Streamlit UI.
- [ ] **Disconnect/crash alerts** — Notify when broker disconnects, 3+ consecutive failures occur, or the bot crashes.

## Phase 5: Observability & Logging
- [ ] **Structured logging** — Add structured JSON logging with log rotation and log every tick decision for post-market analysis.
- [ ] **Performance metrics dashboard** — Extend the Streamlit UI with: win rate, avg win/loss, max drawdown, Sharpe ratio, equity curve chart, and calendar heatmap of daily PnL.
- [ ] **Enrich trade log** — Add columns to `trades.csv`: range_high/low at entry, slippage (expected vs fill price), exit reason, strategy state at time of trade.

## Phase 6: Persistence & Database
- [ ] **SQLite instead of CSV** — Replace CSV logging with SQLite for proper querying, concurrency safety, and easier analytics.
- [ ] **Full state persistence** — Persist complete bot state (not just trades) to survive restarts cleanly, rather than relying on fragile CSV-based recovery.

## Phase 7: Multi-Symbol & Plugin Architecture
- [ ] **Multi-symbol trading** — Refactor `BotRunner` to manage multiple strategy instances running on different symbols concurrently.
- [ ] **Strategy plugin system** — Abstract a `BaseStrategy` interface so new strategies can be added as plugins without modifying core bot infrastructure.

## Phase 8: Backtesting
- [x] **Backtesting engine** — Full intraday backtester replaying exact 5-minute candle data through the ORB strategy logic. CLI (`python -m backtesting`) and Streamlit dashboard (`streamlit run backtesting/app.py`) with equity curve, drawdown, monthly/yearly returns heatmap, trade statistics, PnL distribution, Sharpe/Sortino/Calmar ratios, and downloadable trade log.
- [ ] **Paper vs live analytics** — Compare paper trading results with live execution to measure slippage and execution quality.

## Phase 9: Testing & CI
- [ ] **Unit tests** — Add tests for: `time_utils` (market hour checks), strategy state transitions, CSV logging, position recovery, and paper order simulation.
- [ ] **Integration tests** — Mock the Angel One API to test full tick cycles, reconnection logic, and error paths end-to-end.
- [ ] **CI pipeline** — GitHub Actions (or similar) to run tests, lint (`ruff`/`flake8`), and type-check (`mypy`) on every push.

## Phase 10: Deployment & Operations
- [ ] **Dockerize** — Add `Dockerfile` with health checks and restart policies for consistent deployment.
- [ ] **Process management** — Run the bot as a background service (systemd/supervisor) so it doesn't depend on a Streamlit tab staying open.
- [ ] **Graceful shutdown with position exit** — Current `stop()` doesn't ensure open positions are closed. Add a shutdown hook that force-exits positions before termination.
- [ ] **Scheduled auto-start/stop** — Automatically start the bot at 9:10 AM and stop after 3:30 PM using OS scheduler or built-in scheduling.

## Phase 11: Security Hardening
- [ ] **Secrets management** — `.env` with plaintext credentials is risky. Consider OS keyring, encrypted secrets, or a vault for API keys and TOTP secrets.
- [ ] **Client-side API rate limiting** — Add throttle awareness to avoid hitting Angel One's API rate limits.
- [ ] **UI confirmation dialogs** — Toggling from paper to live mode and other critical actions should require explicit confirmation with audit logging.

---

## 🏁 Recommended Starting Order (highest ROI first)
1. Configurable symbol & position sizing (Phase 1)
2. Stop-loss (Phase 2)
3. Telegram trade notifications (Phase 4)
4. Unit tests (Phase 9)
5. WebSocket streaming (Phase 3)
