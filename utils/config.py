"""
Configuration Loader Module
Loads and validates settings from config.yaml, exposing them as module-level constants.
"""

import os
import logging
from datetime import time
from typing import Dict, Any, List

import yaml

logger = logging.getLogger(__name__)

# Resolve path relative to the project root (one level up from utils/)
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


def _load_yaml() -> Dict[str, Any]:
    """Read and parse config.yaml."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at {_CONFIG_PATH}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config.yaml: {e}")
        raise


def _parse_time(value: str) -> time:
    """Convert an 'HH:MM' string to a datetime.time object."""
    parts = value.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


# ── Load once at import time ──────────────────────────────────────

_cfg = _load_yaml()

# Symbol
SYMBOL_CONFIG: Dict[str, str] = {
    "exchange": _cfg["symbol"]["exchange"],
    "tradingsymbol": _cfg["symbol"]["tradingsymbol"],
    "symboltoken": str(_cfg["symbol"]["symboltoken"]),
}

# Position sizing
POSITION_SIZING_MODE: str = _cfg["position_sizing"]["mode"]
FIXED_QUANTITY: int = int(_cfg["position_sizing"]["fixed_quantity"])
FIXED_CAPITAL: float = float(_cfg["position_sizing"]["fixed_capital"])
PERCENT_OF_CAPITAL: float = float(_cfg["position_sizing"]["percent_of_capital"])
CAPITAL: float = float(_cfg["position_sizing"]["capital"])
LEVERAGE: float = float(_cfg["position_sizing"].get("leverage", 5.0))

# Market timings
MARKET_OPEN: time = _parse_time(_cfg["market_timings"]["market_open"])
MARKET_CLOSE: time = _parse_time(_cfg["market_timings"]["market_close"])
RANGE_END: time = _parse_time(_cfg["market_timings"]["range_end"])
EXIT_TIME: time = _parse_time(_cfg["market_timings"]["exit_time"])

# Bot settings
TICK_INTERVAL: int = int(_cfg["bot"]["tick_interval"])
HEALTH_CHECK_INTERVAL: int = int(_cfg["bot"]["health_check_interval"])
RETRY_DELAYS: List[int] = [int(d) for d in _cfg["bot"]["retry_delays"]]

# Logging
TRADES_LOG_PATH: str = _cfg["logging"]["trades_log_path"]


def compute_quantity(price: float) -> int:
    """
    Return the number of shares to trade based on the configured sizing mode.

    Args:
        price: Current price per share (used for capital-based modes).

    Returns:
        int: Number of shares (minimum 1).
    """
    lev = max(1.0, LEVERAGE)

    if POSITION_SIZING_MODE == "fixed_quantity":
        base = max(1, FIXED_QUANTITY)
    elif POSITION_SIZING_MODE == "fixed_capital":
        base = max(1, int(FIXED_CAPITAL // price))
    elif POSITION_SIZING_MODE == "percent_of_capital":
        amount = CAPITAL * (PERCENT_OF_CAPITAL / 100)
        base = max(1, int(amount // price))
    else:
        logger.warning(f"Unknown position sizing mode '{POSITION_SIZING_MODE}', falling back to 1")
        base = 1

    return max(1, int(base * lev))
