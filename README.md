# ORB Strategy Results

## What `orb_trades.csv` contains
- One row per executed trade.
- Columns: `day`, `or_high`, `or_low`, `position`, `entry_time`, `entry_price`, `exit_time`, `exit_price`, `pnl`, `pnl_pct`.
- `pnl` is per-trade profit/loss in price points (1 unit).
- `pnl_pct` is percentage return for that trade.

## Backtest Summary (2015-02-02 to 2025-08-06)
- Total Trades: 1938
- Winning Trades: 1068
- Losing Trades: 852
- Breakeven Trades: 18
- Win Rate: 55.11%

## Core Performance
- Total P&L (points): 1746.95
- Average P&L per trade (points): 0.90
- Total P&L (% sum of trade returns): 258.37%
- Largest Win (points): 52.35
- Largest Loss (points): -63.80
- Risk-Reward Ratio: 1.19
- Expectancy (points/trade): 0.86

## Drawdown
- Max Drawdown (points equity curve): 130.60 points

## Fixed Capital Interpretation
Assumption: fixed ₹1000 allocated per trade, no compounding, no costs/slippage.

### 1x Leverage
- Total Profit: ₹2583.69
- Final Capital: ₹3583.69
- Max Drawdown: ₹109.53 (7.76%)

### 5x Leverage
- Total Profit: ₹12918.43
- Final Capital: ₹13918.43
- Max Drawdown: ₹547.65 (20.56%)
