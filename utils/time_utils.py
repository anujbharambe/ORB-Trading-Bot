"""
Time Utilities Module for ORB Trading System
Handles all timezone-aware time operations using Asia/Kolkata timezone.
"""

from datetime import datetime, time
import pytz
from typing import Tuple

from utils.config import (
    MARKET_OPEN as _CFG_MARKET_OPEN,
    MARKET_CLOSE as _CFG_MARKET_CLOSE,
    RANGE_END as _CFG_RANGE_END,
    EXIT_TIME as _CFG_EXIT_TIME,
)


class TimeManager:
    """
    Manages all time-related operations for the trading system.
    All times are in Asia/Kolkata (IST) timezone.
    """
    
    # Indian Standard Time zone
    IST = pytz.timezone('Asia/Kolkata')
    
    # Market timing constants (loaded from config.yaml)
    MARKET_OPEN = _CFG_MARKET_OPEN
    MARKET_CLOSE = _CFG_MARKET_CLOSE
    RANGE_END = _CFG_RANGE_END
    EXIT_TIME = _CFG_EXIT_TIME
    
    @classmethod
    def get_current_time(cls) -> datetime:
        """
        Get current time in IST timezone.
        
        Returns:
            datetime: Current datetime in IST
        """
        return datetime.now(cls.IST)
    
    @classmethod
    def get_today_date(cls) -> str:
        """
        Get today's date string in YYYY-MM-DD format.
        
        Returns:
            str: Today's date string
        """
        return cls.get_current_time().strftime('%Y-%m-%d')
    
    @classmethod
    def is_market_open(cls) -> bool:
        """
        Check if the market is currently open (9:15 AM - 3:30 PM IST).
        
        Returns:
            bool: True if market is open, False otherwise
        """
        current = cls.get_current_time()
        current_time = current.time()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if current.weekday() >= 5:  # Saturday or Sunday
            return False
        
        return cls.MARKET_OPEN <= current_time <= cls.MARKET_CLOSE
    
    @classmethod
    def is_range_building_period(cls) -> bool:
        """
        Check if we're in the opening range building period (9:15 AM - 11:15 AM IST).
        
        Returns:
            bool: True if in range building period
        """
        current_time = cls.get_current_time().time()
        return cls.MARKET_OPEN <= current_time < cls.RANGE_END
    
    @classmethod
    def is_trading_period(cls) -> bool:
        """
        Check if we're in the trading period (11:15 AM - 3:20 PM IST).
        
        Returns:
            bool: True if in trading period
        """
        current_time = cls.get_current_time().time()
        return cls.RANGE_END <= current_time < cls.EXIT_TIME
    
    @classmethod
    def is_exit_time(cls) -> bool:
        """
        Check if it's time to exit positions (3:20 PM IST or later).
        
        Returns:
            bool: True if it's exit time
        """
        current_time = cls.get_current_time().time()
        return current_time >= cls.EXIT_TIME
    
    @classmethod
    def get_strategy_state(cls) -> str:
        """
        Get the current strategy state based on time.
        
        Returns:
            str: Current strategy state
        """
        if not cls.is_market_open():
            return "MARKET_CLOSED"
        elif cls.is_range_building_period():
            return "BUILDING_RANGE"
        elif cls.is_trading_period():
            return "TRADING"
        elif cls.is_exit_time():
            return "EXIT_PERIOD"
        else:
            return "UNKNOWN"
    
    @classmethod
    def format_timestamp(cls, dt: datetime = None) -> str:
        """
        Format datetime to readable string.
        
        Args:
            dt: datetime object (defaults to current time if None)
            
        Returns:
            str: Formatted timestamp string
        """
        if dt is None:
            dt = cls.get_current_time()
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    @classmethod
    def get_seconds_until(cls, target_time: time) -> int:
        """
        Calculate seconds until a specific time today.
        
        Args:
            target_time: Target time to calculate seconds until
            
        Returns:
            int: Seconds until target time (negative if past)
        """
        current = cls.get_current_time()
        target_dt = current.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            microsecond=0
        )
        delta = target_dt - current
        return int(delta.total_seconds())
    
    @classmethod
    def is_new_trading_day(cls, last_date: str) -> bool:
        """
        Check if today is a new trading day compared to last recorded date.
        
        Args:
            last_date: Last recorded trading date (YYYY-MM-DD format)
            
        Returns:
            bool: True if today is a new trading day
        """
        today = cls.get_today_date()
        return today != last_date
    
    @classmethod
    def get_time_display(cls) -> dict:
        """
        Get formatted time information for display.
        
        Returns:
            dict: Time information for UI display
        """
        current = cls.get_current_time()
        return {
            'current_time': cls.format_timestamp(current),
            'market_open': cls.MARKET_OPEN.strftime('%H:%M'),
            'market_close': cls.MARKET_CLOSE.strftime('%H:%M'),
            'range_end': cls.RANGE_END.strftime('%H:%M'),
            'exit_time': cls.EXIT_TIME.strftime('%H:%M'),
            'state': cls.get_strategy_state(),
            'is_weekend': current.weekday() >= 5
        }
