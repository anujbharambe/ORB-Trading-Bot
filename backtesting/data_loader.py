"""
Data Loader Module for Backtesting
Loads and validates user-provided 5-minute candle CSV data.
"""

import os
import logging
from datetime import date, time
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Project root (one level up from backtesting/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


def resolve_csv_path(symbol: str) -> str:
    """
    Resolve the CSV file path from a trading symbol.

    Maps 'RELIANCE-EQ' → 'data/RELIANCE_5minute.csv'.

    Args:
        symbol: Trading symbol (e.g. 'RELIANCE-EQ').

    Returns:
        Absolute path to the CSV file.

    Raises:
        FileNotFoundError: If the resolved CSV does not exist.
    """
    # Strip exchange suffix (-EQ, -BE, etc.)
    base = symbol.split("-")[0]
    filename = f"{base}_5minute.csv"
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"Please place your 5-minute candle CSV at: data/{filename}"
        )
    return path


def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load and validate a 5-minute candle CSV.

    Expected columns: date, open, high, low, close, volume
    Date format: 'YYYY-MM-DD HH:MM:SS'

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with 'date' parsed as datetime and set as index,
        sorted chronologically.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Loading data from {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["date"])

    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Expected: {sorted(required)}"
        )

    df = df.sort_values("date").reset_index(drop=True)
    df.set_index("date", inplace=True)

    logger.info(
        f"Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}"
    )
    return df


def get_trading_days(
    df: pd.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[date]:
    """
    Return a sorted list of unique trading dates in the dataset.

    Args:
        df: DataFrame with DatetimeIndex.
        start_date: Optional filter — only include dates >= start_date.
        end_date: Optional filter — only include dates <= end_date.

    Returns:
        Sorted list of datetime.date objects.
    """
    dates = sorted(df.index.date)
    unique_dates = sorted(set(dates))

    if start_date is not None:
        unique_dates = [d for d in unique_dates if d >= start_date]
    if end_date is not None:
        unique_dates = [d for d in unique_dates if d <= end_date]

    return unique_dates


def get_day_candles(df: pd.DataFrame, day: date) -> pd.DataFrame:
    """
    Extract all candles for a single trading day.

    Args:
        df: DataFrame with DatetimeIndex.
        day: The trading date.

    Returns:
        DataFrame slice for that day, sorted by time.
    """
    mask = df.index.date == day
    return df.loc[mask].sort_index()


def get_range_candles(day_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract candles in the opening-range-building period (09:15 – 11:15).

    Args:
        day_df: Candles for a single trading day.

    Returns:
        Candles within the range-building window.
    """
    range_start = time(9, 15)
    range_end = time(11, 15)
    mask = (day_df.index.time >= range_start) & (day_df.index.time < range_end)
    return day_df.loc[mask]


def get_trading_candles(day_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract candles in the breakout-trading period (11:15 – 15:20 inclusive).

    Args:
        day_df: Candles for a single trading day.

    Returns:
        Candles within the trading window.
    """
    trade_start = time(11, 15)
    trade_end = time(15, 20)
    mask = (day_df.index.time >= trade_start) & (day_df.index.time <= trade_end)
    return day_df.loc[mask]


def get_exit_candle(day_df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Get the 15:20 candle used for end-of-day exit.

    Args:
        day_df: Candles for a single trading day.

    Returns:
        The 15:20 candle as a Series, or the last candle at or after 15:15
        if 15:20 is missing.  Returns None if no suitable candle exists.
    """
    exit_time = time(15, 20)
    exact = day_df[day_df.index.time == exit_time]
    if not exact.empty:
        return exact.iloc[0]

    # Fallback: last candle at 15:15 or later
    fallback = day_df[day_df.index.time >= time(15, 15)]
    if not fallback.empty:
        return fallback.iloc[-1]

    return None
