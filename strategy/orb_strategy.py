"""
Opening Range Breakout (ORB) Strategy Module
Implements the ORB trading strategy for NSE stocks.
"""

import os
import csv
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from utils.time_utils import TimeManager
from broker.angel_client import AngelOneClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyState(Enum):
    """Enum for strategy states."""
    IDLE = "IDLE"
    BUILDING_RANGE = "BUILDING_RANGE"
    WAITING_FOR_BREAKOUT = "WAITING_FOR_BREAKOUT"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_CLOSED = "POSITION_CLOSED"
    MARKET_CLOSED = "MARKET_CLOSED"
    ERROR = "ERROR"


class PositionType(Enum):
    """Enum for position types."""
    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    """Represents a single trade."""
    timestamp: str
    action: str  # 'BUY', 'SELL', 'EXIT_LONG', 'EXIT_SHORT'
    price: float
    quantity: int
    position_type: str
    pnl: float = 0.0
    order_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            'timestamp': self.timestamp,
            'action': self.action,
            'price': self.price,
            'quantity': self.quantity,
            'position_type': self.position_type,
            'pnl': self.pnl,
            'order_id': self.order_id
        }


@dataclass 
class ORBState:
    """Holds the current state of the ORB strategy."""
    # Opening range
    range_high: Optional[float] = None
    range_low: Optional[float] = None
    range_complete: bool = False
    
    # Current position
    position: PositionType = PositionType.NONE
    entry_price: float = 0.0
    current_price: float = 0.0
    quantity: int = 1
    
    # Trade tracking
    trade_taken_today: bool = False
    last_trade_date: str = ""
    
    # PnL
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Strategy state
    strategy_state: StrategyState = StrategyState.IDLE
    last_update: str = ""
    error_message: str = ""
    
    # Trade history
    trades: List[Trade] = field(default_factory=list)


class ORBStrategy:
    """
    Opening Range Breakout Strategy Implementation.
    
    Strategy Rules:
    1. Build opening range from 9:15 AM to 11:15 AM IST
    2. After 11:15 AM, enter LONG on range high breakout, SHORT on range low breakdown
    3. Only ONE trade per day
    4. Exit at 3:20 PM
    5. No stop loss
    6. Position size: 1 share
    """
    
    POSITION_SIZE = 1
    TRADES_LOG_PATH = "logs/trades.csv"
    
    def __init__(self, broker: AngelOneClient):
        """
        Initialize ORB Strategy.
        
        Args:
            broker: AngelOneClient instance for market data and order execution
        """
        self.broker = broker
        self.state = ORBState()
        self.is_running = False
        self._ensure_logs_directory()
        self._initialize_csv_log()
        
    def _ensure_logs_directory(self) -> None:
        """Ensure logs directory exists."""
        os.makedirs("logs", exist_ok=True)
        
    def _initialize_csv_log(self) -> None:
        """Initialize CSV trade log with headers if not exists."""
        if not os.path.exists(self.TRADES_LOG_PATH):
            with open(self.TRADES_LOG_PATH, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'action', 'price', 'quantity', 
                    'position_type', 'pnl', 'order_id'
                ])
    
    def _log_trade(self, trade: Trade) -> None:
        """
        Log trade to CSV file.
        
        Args:
            trade: Trade object to log
        """
        try:
            with open(self.TRADES_LOG_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade.timestamp,
                    trade.action,
                    trade.price,
                    trade.quantity,
                    trade.position_type,
                    trade.pnl,
                    trade.order_id
                ])
            logger.info(f"Trade logged: {trade.action} at {trade.price}")
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def reset_daily_state(self) -> None:
        """Reset strategy state for a new trading day."""
        today = TimeManager.get_today_date()
        
        if TimeManager.is_new_trading_day(self.state.last_trade_date):
            logger.info(f"New trading day detected: {today}. Resetting state.")
            self.state = ORBState()
            self.state.last_trade_date = today
            self.state.strategy_state = StrategyState.IDLE
    
    def update_range(self, price: float) -> None:
        """
        Update opening range with new price during range building period.
        
        Args:
            price: Current LTP
        """
        if self.state.range_complete:
            return
            
        if self.state.range_high is None or price > self.state.range_high:
            self.state.range_high = price
            logger.debug(f"Range high updated: {price}")
            
        if self.state.range_low is None or price < self.state.range_low:
            self.state.range_low = price
            logger.debug(f"Range low updated: {price}")
    
    def finalize_range(self) -> None:
        """Mark opening range as complete."""
        if not self.state.range_complete:
            self.state.range_complete = True
            logger.info(f"Opening range finalized - High: {self.state.range_high}, Low: {self.state.range_low}")
    
    def check_breakout(self, price: float) -> Optional[PositionType]:
        """
        Check for breakout above range high or below range low.
        
        Args:
            price: Current LTP
            
        Returns:
            PositionType: LONG for upside breakout, SHORT for downside, NONE if no breakout
        """
        if not self.state.range_complete:
            return PositionType.NONE
            
        if self.state.trade_taken_today:
            return PositionType.NONE
            
        if self.state.range_high is not None and price >= self.state.range_high:
            logger.info(f"BREAKOUT DETECTED: Price {price} >= Range High {self.state.range_high}")
            return PositionType.LONG
            
        if self.state.range_low is not None and price <= self.state.range_low:
            logger.info(f"BREAKDOWN DETECTED: Price {price} <= Range Low {self.state.range_low}")
            return PositionType.SHORT
            
        return PositionType.NONE
    
    def enter_position(self, position_type: PositionType, price: float) -> bool:
        """
        Enter a new position.
        
        Args:
            position_type: LONG or SHORT
            price: Entry price
            
        Returns:
            bool: True if position entered successfully
        """
        if self.state.trade_taken_today:
            logger.warning("Trade already taken today. Skipping entry.")
            return False
            
        transaction_type = "BUY" if position_type == PositionType.LONG else "SELL"
        
        # Place order via broker
        order_result = self.broker.place_order(
            transaction_type=transaction_type,
            quantity=self.POSITION_SIZE
        )
        
        if order_result['status']:
            self.state.position = position_type
            self.state.entry_price = order_result.get('price', price)
            self.state.quantity = self.POSITION_SIZE
            self.state.trade_taken_today = True
            self.state.strategy_state = StrategyState.POSITION_OPEN
            
            # Log the trade
            trade = Trade(
                timestamp=TimeManager.format_timestamp(),
                action=transaction_type,
                price=self.state.entry_price,
                quantity=self.POSITION_SIZE,
                position_type=position_type.value,
                order_id=order_result.get('order_id', '')
            )
            self.state.trades.append(trade)
            self._log_trade(trade)
            
            logger.info(f"Entered {position_type.value} position at {self.state.entry_price}")
            return True
        else:
            logger.error(f"Failed to enter position: {order_result['message']}")
            self.state.error_message = order_result['message']
            return False
    
    def exit_position(self, price: float, reason: str = "EXIT") -> bool:
        """
        Exit current position.
        
        Args:
            price: Exit price
            reason: Reason for exit (for logging)
            
        Returns:
            bool: True if position exited successfully
        """
        if self.state.position == PositionType.NONE:
            logger.warning("No position to exit.")
            return False
            
        # Determine transaction type for exit
        if self.state.position == PositionType.LONG:
            transaction_type = "SELL"
            action = "EXIT_LONG"
        else:
            transaction_type = "BUY"
            action = "EXIT_SHORT"
        
        # Place exit order
        order_result = self.broker.place_order(
            transaction_type=transaction_type,
            quantity=self.state.quantity
        )
        
        if order_result['status']:
            exit_price = order_result.get('price', price)
            
            # Calculate PnL
            if self.state.position == PositionType.LONG:
                pnl = (exit_price - self.state.entry_price) * self.state.quantity
            else:  # SHORT
                pnl = (self.state.entry_price - exit_price) * self.state.quantity
            
            self.state.realized_pnl += pnl
            
            # Log the exit trade
            trade = Trade(
                timestamp=TimeManager.format_timestamp(),
                action=action,
                price=exit_price,
                quantity=self.state.quantity,
                position_type=self.state.position.value,
                pnl=pnl,
                order_id=order_result.get('order_id', '')
            )
            self.state.trades.append(trade)
            self._log_trade(trade)
            
            logger.info(f"Exited {self.state.position.value} position at {exit_price}. PnL: {pnl}")
            
            # Reset position
            self.state.position = PositionType.NONE
            self.state.entry_price = 0.0
            self.state.unrealized_pnl = 0.0
            self.state.strategy_state = StrategyState.POSITION_CLOSED
            
            return True
        else:
            logger.error(f"Failed to exit position: {order_result['message']}")
            self.state.error_message = order_result['message']
            return False
    
    def update_unrealized_pnl(self, current_price: float) -> None:
        """
        Update unrealized PnL based on current price.
        
        Args:
            current_price: Current market price
        """
        if self.state.position == PositionType.NONE:
            self.state.unrealized_pnl = 0.0
            return
            
        if self.state.position == PositionType.LONG:
            self.state.unrealized_pnl = (current_price - self.state.entry_price) * self.state.quantity
        else:  # SHORT
            self.state.unrealized_pnl = (self.state.entry_price - current_price) * self.state.quantity
    
    def tick(self) -> Dict[str, Any]:
        """
        Main strategy tick - called periodically (every 5 seconds).
        Fetches price and executes strategy logic.
        
        Returns:
            dict: Current strategy state summary
        """
        if not self.is_running:
            return self.get_state_summary()
        
        # Reset for new trading day
        self.reset_daily_state()
        
        # Update timestamp
        self.state.last_update = TimeManager.format_timestamp()
        
        # Check market hours
        if not TimeManager.is_market_open():
            self.state.strategy_state = StrategyState.MARKET_CLOSED
            return self.get_state_summary()
        
        # Fetch current price
        price = self.broker.get_ltp()
        if price is None:
            self.state.error_message = "Failed to fetch LTP"
            self.state.strategy_state = StrategyState.ERROR
            return self.get_state_summary()
        
        self.state.current_price = price
        self.state.error_message = ""
        
        # Strategy logic based on time period
        if TimeManager.is_range_building_period():
            # Building the opening range
            self.state.strategy_state = StrategyState.BUILDING_RANGE
            self.update_range(price)
            
        elif TimeManager.is_trading_period():
            # Finalize range if not done
            if not self.state.range_complete:
                self.finalize_range()
            
            # Check for exit time first
            if TimeManager.is_exit_time():
                if self.state.position != PositionType.NONE:
                    self.exit_position(price, "END_OF_DAY")
                self.state.strategy_state = StrategyState.POSITION_CLOSED
            
            # If no position, look for breakout
            elif self.state.position == PositionType.NONE:
                self.state.strategy_state = StrategyState.WAITING_FOR_BREAKOUT
                
                if not self.state.trade_taken_today:
                    breakout = self.check_breakout(price)
                    if breakout != PositionType.NONE:
                        self.enter_position(breakout, price)
            
            # If in position, update unrealized PnL
            else:
                self.state.strategy_state = StrategyState.POSITION_OPEN
                self.update_unrealized_pnl(price)
        
        elif TimeManager.is_exit_time():
            # Exit period - close any open position
            if self.state.position != PositionType.NONE:
                self.exit_position(price, "END_OF_DAY")
            self.state.strategy_state = StrategyState.POSITION_CLOSED
        
        return self.get_state_summary()
    
    def start(self) -> bool:
        """
        Start the strategy.
        
        Returns:
            bool: True if started successfully
        """
        if self.is_running:
            logger.warning("Strategy is already running")
            return False
        
        # Connect to broker
        if not self.broker.is_connected:
            if not self.broker.connect():
                logger.error("Failed to connect to broker")
                self.state.error_message = "Failed to connect to broker"
                return False
        
        self.is_running = True
        self.state.last_trade_date = TimeManager.get_today_date()
        logger.info("ORB Strategy started")
        return True
    
    def stop(self) -> bool:
        """
        Stop the strategy (does not exit positions automatically).
        
        Returns:
            bool: True if stopped successfully
        """
        self.is_running = False
        logger.info("ORB Strategy stopped")
        return True
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get current strategy state as dictionary.
        
        Returns:
            dict: Current strategy state
        """
        return {
            'is_running': self.is_running,
            'strategy_state': self.state.strategy_state.value,
            'range_high': self.state.range_high,
            'range_low': self.state.range_low,
            'range_complete': self.state.range_complete,
            'current_price': self.state.current_price,
            'position': self.state.position.value,
            'entry_price': self.state.entry_price,
            'quantity': self.state.quantity,
            'unrealized_pnl': round(self.state.unrealized_pnl, 2),
            'realized_pnl': round(self.state.realized_pnl, 2),
            'trade_taken_today': self.state.trade_taken_today,
            'last_update': self.state.last_update,
            'error_message': self.state.error_message,
            'trades_today': len([t for t in self.state.trades if TimeManager.get_today_date() in t.timestamp]),
            'broker_status': self.broker.connection_status
        }
    
    def get_trade_history(self) -> List[Dict]:
        """
        Get trade history.
        
        Returns:
            list: List of trade dictionaries
        """
        return [t.to_dict() for t in self.state.trades]
