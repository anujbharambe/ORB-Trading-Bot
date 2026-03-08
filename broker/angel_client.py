"""
Angel One SmartAPI Client Module
Handles all broker interactions including authentication, data fetching, and order placement.
"""

import os
import logging
from typing import Optional, Dict, Any
from SmartApi import SmartConnect
from SmartApi.smartExceptions import TokenException, DataException
import pyotp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AngelOneClient:
    """
    Wrapper class for Angel One SmartAPI.
    Handles authentication, LTP fetching, and order placement.
    """
    
    # Symbol configuration for Reliance Industries
    RELIANCE_CONFIG = {
        'exchange': 'NSE',
        'tradingsymbol': 'RELIANCE-EQ',
        'symboltoken': '2885',  # NSE token for Reliance
    }
    
    def __init__(self, paper_trading: bool = True):
        """
        Initialize Angel One client.
        
        Args:
            paper_trading: If True, simulate orders instead of placing real ones
        """
        self.paper_trading = paper_trading
        self.smart_api: Optional[SmartConnect] = None
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.is_connected: bool = False
        
        # Load credentials from environment
        self.api_key = os.getenv('ANGEL_API_KEY', '')
        self.client_id = os.getenv('ANGEL_CLIENT_ID', '')
        self.password = os.getenv('ANGEL_PASSWORD', '')
        self.totp_token = os.getenv('ANGEL_TOTP', '')
        
    def _generate_totp(self) -> str:
        """
        Generate TOTP for 2FA authentication.
        
        Returns:
            str: Generated TOTP code
        """
        try:
            totp = pyotp.TOTP(self.totp_token)
            return totp.now()
        except Exception as e:
            logger.error(f"Error generating TOTP: {e}")
            raise
    
    def connect(self) -> bool:
        """
        Establish connection to Angel One SmartAPI.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Validate credentials
            if not all([self.api_key, self.client_id, self.password, self.totp_token]):
                logger.error("Missing API credentials. Check your .env file.")
                return False
            
            # Initialize SmartAPI
            self.smart_api = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP
            totp = self._generate_totp()
            
            # Login
            logger.info(f"Attempting to connect as client: {self.client_id}")
            session_data = self.smart_api.generateSession(
                clientCode=self.client_id,
                password=self.password,
                totp=totp
            )
            
            if session_data['status']:
                self.auth_token = session_data['data']['jwtToken']
                self.refresh_token = session_data['data']['refreshToken']
                self.feed_token = self.smart_api.getfeedToken()
                self.is_connected = True
                logger.info("Successfully connected to Angel One SmartAPI")
                return True
            else:
                logger.error(f"Login failed: {session_data.get('message', 'Unknown error')}")
                return False
                
        except TokenException as e:
            logger.error(f"Token exception during login: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Logout from Angel One SmartAPI.
        
        Returns:
            bool: True if logout successful
        """
        try:
            if self.smart_api and self.is_connected:
                self.smart_api.terminateSession(self.client_id)
                logger.info("Successfully disconnected from Angel One")
            self.is_connected = False
            return True
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.is_connected = False
            return True
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect if session expired.
        
        Returns:
            bool: True if reconnection successful
        """
        logger.info("Attempting to reconnect...")
        self.disconnect()
        return self.connect()
    
    def get_ltp(self, symbol_config: Dict = None) -> Optional[float]:
        """
        Fetch Last Traded Price for a symbol.
        
        Args:
            symbol_config: Symbol configuration dict (defaults to Reliance)
            
        Returns:
            float: Last traded price, or None if fetch fails
        """
        if symbol_config is None:
            symbol_config = self.RELIANCE_CONFIG
            
        try:
            if not self.is_connected:
                logger.warning("Not connected. Attempting to connect...")
                if not self.connect():
                    return None
            
            ltp_data = self.smart_api.ltpData(
                exchange=symbol_config['exchange'],
                tradingsymbol=symbol_config['tradingsymbol'],
                symboltoken=symbol_config['symboltoken']
            )
            
            if ltp_data['status']:
                ltp = float(ltp_data['data']['ltp'])
                logger.debug(f"LTP for {symbol_config['tradingsymbol']}: {ltp}")
                return ltp
            else:
                logger.error(f"Failed to fetch LTP: {ltp_data.get('message', 'Unknown error')}")
                return None
                
        except TokenException as e:
            logger.error(f"Token expired: {e}. Attempting reconnect...")
            if self.reconnect():
                return self.get_ltp(symbol_config)
            return None
        except DataException as e:
            logger.error(f"Data exception while fetching LTP: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            return None
    
    def get_quote(self, symbol_config: Dict = None) -> Optional[Dict]:
        """
        Fetch full quote data for a symbol.
        
        Args:
            symbol_config: Symbol configuration dict (defaults to Reliance)
            
        Returns:
            dict: Quote data including open, high, low, close, etc.
        """
        if symbol_config is None:
            symbol_config = self.RELIANCE_CONFIG
            
        try:
            if not self.is_connected:
                if not self.connect():
                    return None
            
            quote_data = self.smart_api.getMarketData(
                mode='FULL',
                exchangeTokens={
                    symbol_config['exchange']: [symbol_config['symboltoken']]
                }
            )
            
            if quote_data['status']:
                return quote_data['data']
            else:
                logger.error(f"Failed to fetch quote: {quote_data.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return None
    
    def place_order(
        self,
        transaction_type: str,  # 'BUY' or 'SELL'
        quantity: int = 1,
        symbol_config: Dict = None,
        order_type: str = 'MARKET',
        product_type: str = 'INTRADAY'  # MIS for intraday
    ) -> Dict[str, Any]:
        """
        Place an order (real or paper).
        
        Args:
            transaction_type: 'BUY' or 'SELL'
            quantity: Number of shares
            symbol_config: Symbol configuration dict
            order_type: 'MARKET' or 'LIMIT'
            product_type: 'INTRADAY' (MIS) or 'DELIVERY'
            
        Returns:
            dict: Order response with status and order_id
        """
        if symbol_config is None:
            symbol_config = self.RELIANCE_CONFIG
            
        order_result = {
            'status': False,
            'order_id': None,
            'message': '',
            'paper_trade': self.paper_trading
        }
        
        # Paper trading mode - simulate order
        if self.paper_trading:
            ltp = self.get_ltp(symbol_config)
            if ltp:
                order_result['status'] = True
                order_result['order_id'] = f"PAPER_{transaction_type}_{int(ltp * 100)}"
                order_result['message'] = f"Paper order placed: {transaction_type} {quantity} {symbol_config['tradingsymbol']} at {ltp}"
                order_result['price'] = ltp
                logger.info(order_result['message'])
            else:
                order_result['message'] = "Failed to get LTP for paper order"
                logger.error(order_result['message'])
            return order_result
        
        # Real order placement
        try:
            if not self.is_connected:
                if not self.connect():
                    order_result['message'] = "Not connected to broker"
                    return order_result
            
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol_config['tradingsymbol'],
                "symboltoken": symbol_config['symboltoken'],
                "transactiontype": transaction_type,
                "exchange": symbol_config['exchange'],
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "quantity": quantity
            }
            
            if order_type == 'LIMIT':
                order_params['price'] = self.get_ltp(symbol_config)
            
            response = self.smart_api.placeOrder(order_params)
            
            if response:
                order_result['status'] = True
                order_result['order_id'] = response
                order_result['message'] = f"Order placed: {transaction_type} {quantity} {symbol_config['tradingsymbol']}"
                order_result['price'] = self.get_ltp(symbol_config)
                logger.info(f"Order placed successfully: {response}")
            else:
                order_result['message'] = "Order placement failed"
                logger.error("Order placement returned None")
                
        except TokenException as e:
            logger.error(f"Token exception during order: {e}")
            order_result['message'] = f"Token error: {e}"
            if self.reconnect():
                return self.place_order(transaction_type, quantity, symbol_config, order_type, product_type)
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            order_result['message'] = f"Order error: {e}"
            
        return order_result
    
    def get_positions(self) -> Optional[Dict]:
        """
        Get current positions.
        
        Returns:
            dict: Position data or None if fetch fails
        """
        try:
            if not self.is_connected:
                if not self.connect():
                    return None
            
            positions = self.smart_api.position()
            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return None
    
    def get_order_book(self) -> Optional[Dict]:
        """
        Get order book.
        
        Returns:
            dict: Order book data or None if fetch fails
        """
        try:
            if not self.is_connected:
                if not self.connect():
                    return None
            
            orders = self.smart_api.orderBook()
            return orders
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return None
    
    @property
    def connection_status(self) -> str:
        """Get human-readable connection status."""
        if self.is_connected:
            mode = "Paper Trading" if self.paper_trading else "Live Trading"
            return f"Connected ({mode})"
        return "Disconnected"
