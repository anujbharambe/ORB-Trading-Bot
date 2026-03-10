"""
Backtesting Engine for ORB Strategy
Replays exact 5-minute candle data through the Opening Range Breakout logic.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, List, Optional

import pandas as pd

from backtesting.data_loader import (
    get_day_candles,
    get_exit_candle,
    get_range_candles,
    get_trading_candles,
    get_trading_days,
    load_data,
    resolve_csv_path,
)

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────


@dataclass
class BacktestConfig:
    """All tuneable parameters for a backtest run."""

    symbol: str = "RELIANCE-EQ"
    csv_path: str = ""  # auto-resolved from symbol if empty

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    initial_capital: float = 100_000.0

    # Position sizing (mirrors utils/config.py modes)
    position_sizing_mode: str = "fixed_quantity"
    fixed_quantity: int = 1
    fixed_capital: float = 10_000.0
    percent_of_capital: float = 5.0

    # Leverage
    leverage: float = 5.0  # margin multiplier applied to position size

    # Costs
    commission_pct: float = 0.05  # total round-trip cost as % of trade value
    slippage_pct: float = 0.05  # per-side slippage as % of price


# ── Result container ───────────────────────────────────────────────


@dataclass
class BacktestResult:
    """Holds the output of a completed backtest."""

    trades: List[Dict] = field(default_factory=list)
    daily_equity: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    config: BacktestConfig = field(default_factory=BacktestConfig)


# ── Engine ─────────────────────────────────────────────────────────


class BacktestEngine:
    """
    Replays exact 5-minute intraday data through the ORB strategy.

    Per trading day:
    1. 09:15 – 11:15  →  Build opening range (max high / min low).
    2. 11:15 – 15:20  →  Scan for first breakout above range_high (LONG)
                          or below range_low (SHORT).
    3. Entry at breakout boundary ± slippage.
    4. Exit at 15:20 candle close ± slippage.
    5. One trade per day maximum.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config

    # ── public API ─────────────────────────────────────────────────

    def run(self) -> BacktestResult:
        """Execute the backtest and return results."""
        cfg = self.config

        # Resolve data path
        csv_path = cfg.csv_path or resolve_csv_path(cfg.symbol)
        df = load_data(csv_path)

        trading_days = get_trading_days(df, cfg.start_date, cfg.end_date)
        logger.info(
            f"Backtesting {cfg.symbol} over {len(trading_days)} trading days "
            f"({trading_days[0]} -> {trading_days[-1]})"
        )

        trades: List[Dict] = []
        equity = cfg.initial_capital
        equity_records: List[Dict] = []

        for day in trading_days:
            day_candles = get_day_candles(df, day)
            trade = self._simulate_day(day, day_candles, equity)

            if trade is not None:
                equity += trade["net_pnl"]
                trades.append(trade)

            equity_records.append({"date": day, "equity": equity})

        equity_df = pd.DataFrame(equity_records)
        if not equity_df.empty:
            equity_df["date"] = pd.to_datetime(equity_df["date"])
            equity_df.set_index("date", inplace=True)

        result = BacktestResult(
            trades=trades,
            daily_equity=equity_df,
            config=cfg,
        )
        logger.info(
            f"Backtest complete -- {len(trades)} trades, "
            f"final equity: {equity:,.2f}"
        )
        return result

    # ── private helpers ────────────────────────────────────────────

    def _simulate_day(
        self, day: date, day_candles: pd.DataFrame, current_equity: float
    ) -> Optional[Dict]:
        """
        Simulate ORB strategy for a single trading day.

        Returns a trade dict or None if no trade was triggered.
        """
        # 1. Build opening range
        range_candles = get_range_candles(day_candles)
        if range_candles.empty:
            return None

        range_high = range_candles["high"].max()
        range_low = range_candles["low"].min()

        if range_high == range_low:
            return None  # flat range -- no trade possible

        # 2. Scan trading candles for breakout
        trading_candles = get_trading_candles(day_candles)
        if trading_candles.empty:
            return None

        direction = None
        entry_price = None
        breakout_time = None

        for ts, candle in trading_candles.iterrows():
            if candle["high"] >= range_high:
                if direction is None:
                    direction = "LONG"
                    entry_price = range_high
                    breakout_time = ts
                    break
            if candle["low"] <= range_low:
                if direction is None:
                    direction = "SHORT"
                    entry_price = range_low
                    breakout_time = ts
                    break

        if direction is None:
            return None  # no breakout today

        # 3. Determine exit
        exit_candle = get_exit_candle(day_candles)
        if exit_candle is None:
            return None  # shouldn't happen, but safety check

        exit_price = exit_candle["close"]

        # 4. Apply slippage
        slip = self.config.slippage_pct / 100.0
        if direction == "LONG":
            entry_price_adj = entry_price * (1.0 + slip)
            exit_price_adj = exit_price * (1.0 - slip)
        else:  # SHORT
            entry_price_adj = entry_price * (1.0 - slip)
            exit_price_adj = exit_price * (1.0 + slip)

        # 5. Compute position size
        quantity = self._compute_quantity(entry_price_adj, current_equity)

        # 6. Compute PnL
        if direction == "LONG":
            gross_pnl = (exit_price_adj - entry_price_adj) * quantity
        else:
            gross_pnl = (entry_price_adj - exit_price_adj) * quantity

        trade_value = (entry_price_adj + exit_price_adj) * quantity
        commission = trade_value * (self.config.commission_pct / 100.0)
        net_pnl = gross_pnl - commission

        return {
            "date": day,
            "direction": direction,
            "range_high": range_high,
            "range_low": range_low,
            "entry_price": round(entry_price_adj, 2),
            "exit_price": round(exit_price_adj, 2),
            "quantity": quantity,
            "gross_pnl": round(gross_pnl, 2),
            "commission": round(commission, 2),
            "net_pnl": round(net_pnl, 2),
            "entry_time": str(breakout_time),
            "exit_time": str(exit_candle.name),
        }

    def _compute_quantity(self, price: float, current_equity: float) -> int:
        """Compute position size based on config mode, then apply leverage."""
        mode = self.config.position_sizing_mode
        leverage = max(1.0, self.config.leverage)

        if mode == "fixed_quantity":
            base = max(1, self.config.fixed_quantity)
        elif mode == "fixed_capital":
            base = max(1, int(self.config.fixed_capital // price))
        elif mode == "percent_of_capital":
            amount = current_equity * (self.config.percent_of_capital / 100.0)
            base = max(1, int(amount // price))
        else:
            logger.warning(f"Unknown sizing mode '{mode}', falling back to 1")
            base = 1

        return max(1, int(base * leverage))
