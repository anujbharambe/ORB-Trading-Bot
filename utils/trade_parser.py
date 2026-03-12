"""
Trade Parser Module
Converts live trade CSV logs into the analytics-compatible format used by
the backtesting engine, enabling full performance metrics on forward trades.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd

from utils.config import TRADES_LOG_PATH, CAPITAL


@dataclass
class LiveResult:
    """Duck-typed equivalent of BacktestResult for the analytics module."""

    trades: List[Dict] = field(default_factory=list)
    daily_equity: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    config: "LiveConfig" = None  # type: ignore[assignment]


@dataclass
class LiveConfig:
    """Minimal config object that analytics.compute_metrics() expects."""

    initial_capital: float = 0.0
    symbol: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


def parse_trades(
    csv_path: str = TRADES_LOG_PATH,
    initial_capital: Optional[float] = None,
) -> Optional[LiveResult]:
    """
    Read the live trades CSV and return a LiveResult suitable for
    ``backtesting.analytics.compute_metrics()``.

    Returns None if the CSV is missing or contains no completed trades.
    """
    try:
        df = pd.read_csv(csv_path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None

    if df.empty:
        return None

    capital = initial_capital if initial_capital is not None else CAPITAL

    # Normalise column names (strip whitespace)
    df.columns = df.columns.str.strip()

    trades = _pair_trades(df)
    if not trades:
        return None

    equity_df = _build_equity(trades, capital)

    config = LiveConfig(initial_capital=capital)

    result = LiveResult(trades=trades, daily_equity=equity_df, config=config)
    return result


# ── Internal helpers ───────────────────────────────────────────────


def _pair_trades(df: pd.DataFrame) -> List[Dict]:
    """
    Walk through the CSV and pair each entry row (BUY/SELL) with the
    following exit row (EXIT_LONG/EXIT_SHORT) to produce one trade record.
    Handles old CSV formats (without range_high/range_low/strategy_state)
    by filling defaults.
    """
    entries = df[df["action"].isin(["BUY", "SELL"])]
    exits = df[df["action"].isin(["EXIT_LONG", "EXIT_SHORT"])]

    paired: List[Dict] = []

    for idx, entry_row in entries.iterrows():
        # Find the first exit that comes after this entry
        later_exits = exits[exits.index > idx]
        if later_exits.empty:
            continue  # open position with no exit yet

        exit_row = later_exits.iloc[0]
        # Remove this exit from consideration for future entries
        exits = exits.drop(exit_row.name)

        direction = "LONG" if entry_row["action"] == "BUY" else "SHORT"
        entry_price = float(entry_row["price"])
        exit_price = float(exit_row["price"])
        quantity = int(entry_row["quantity"])

        if direction == "LONG":
            gross_pnl = (exit_price - entry_price) * quantity
        else:
            gross_pnl = (entry_price - exit_price) * quantity

        # Parse trade date from timestamp
        trade_date = _parse_date(str(entry_row["timestamp"]))

        # Range values (may be absent in older CSVs)
        range_high = _safe_float(entry_row.get("range_high"))
        range_low = _safe_float(entry_row.get("range_low"))

        # Exit reason (from exit row)
        exit_reason = str(exit_row.get("exit_reason", "")).strip()
        if not exit_reason:
            exit_reason = "EOD_EXIT"

        paired.append({
            "date": trade_date,
            "direction": direction,
            "range_high": range_high if range_high is not None else 0.0,
            "range_low": range_low if range_low is not None else 0.0,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "quantity": quantity,
            "gross_pnl": round(gross_pnl, 2),
            "commission": 0.0,  # live trades already include broker costs at fill
            "net_pnl": round(gross_pnl, 2),
            "entry_time": str(entry_row["timestamp"]),
            "exit_time": str(exit_row["timestamp"]),
            "exit_reason": exit_reason,
        })

    return paired


def _build_equity(trades: List[Dict], initial_capital: float) -> pd.DataFrame:
    """Build a daily equity curve from paired trades."""
    if not trades:
        return pd.DataFrame()

    # Group trades by date and sum PnL
    daily_pnl: Dict[date, float] = {}
    for t in trades:
        d = t["date"]
        daily_pnl[d] = daily_pnl.get(d, 0.0) + t["net_pnl"]

    dates = sorted(daily_pnl.keys())
    equity = initial_capital
    rows = []
    for d in dates:
        equity += daily_pnl[d]
        rows.append({"date": d, "equity": round(equity, 2)})

    df = pd.DataFrame(rows).set_index("date")
    return df


def _parse_date(ts: str) -> date:
    """Extract a date from a timestamp string like '2026-03-09 14:33:00'."""
    try:
        return datetime.strptime(ts[:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return date.today()


def _safe_float(val) -> Optional[float]:
    """Convert a value to float, returning None for missing/empty."""
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None
    try:
        import math
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None
