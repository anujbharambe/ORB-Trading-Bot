"""
Opening Range Breakout (ORB) Trading Bot - Streamlit Dashboard
Main entry point for the trading application.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime

from broker.angel_client import AngelOneClient
from strategy.orb_strategy import ORBStrategy, StrategyState, PositionType
from utils.time_utils import TimeManager


# Page configuration
st.set_page_config(
    page_title="ORB Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 5px;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .green-text { color: #00ff00; }
    .red-text { color: #ff0000; }
    .yellow-text { color: #ffff00; }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'broker' not in st.session_state:
        st.session_state.broker = AngelOneClient(paper_trading=True)
    
    if 'strategy' not in st.session_state:
        st.session_state.strategy = ORBStrategy(st.session_state.broker)
    
    if 'bot_running' not in st.session_state:
        st.session_state.bot_running = False
    
    if 'last_tick_time' not in st.session_state:
        st.session_state.last_tick_time = 0
    
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True


def get_state_color(state: str) -> str:
    """Get color based on strategy state."""
    color_map = {
        'BUILDING_RANGE': '🟡',
        'WAITING_FOR_BREAKOUT': '🟢',
        'POSITION_OPEN': '🔵',
        'POSITION_CLOSED': '⚪',
        'MARKET_CLOSED': '🔴',
        'ERROR': '🔴',
        'IDLE': '⚪'
    }
    return color_map.get(state, '⚪')


def get_position_color(position: str) -> str:
    """Get color based on position type."""
    if position == 'LONG':
        return '🟢'
    elif position == 'SHORT':
        return '🔴'
    return '⚪'


def format_pnl(pnl: float) -> str:
    """Format PnL with color indicator."""
    if pnl > 0:
        return f"🟢 ₹{pnl:,.2f}"
    elif pnl < 0:
        return f"🔴 ₹{pnl:,.2f}"
    return f"⚪ ₹{pnl:,.2f}"


def render_header():
    """Render page header."""
    col1, col2, col3 = st.columns([2, 3, 2])
    
    with col1:
        st.image("https://via.placeholder.com/100x50?text=ORB+Bot", width=100)
    
    with col2:
        st.title("📈 ORB Trading Bot")
        st.caption("Opening Range Breakout Strategy - Reliance Industries (NSE)")
    
    with col3:
        time_info = TimeManager.get_time_display()
        st.metric("Current Time (IST)", time_info['current_time'].split(' ')[1])


def render_sidebar():
    """Render sidebar with controls and settings."""
    st.sidebar.header("⚙️ Controls")
    
    # Trading mode toggle
    paper_mode = st.sidebar.checkbox(
        "Paper Trading Mode", 
        value=st.session_state.broker.paper_trading,
        help="When enabled, simulates trades without real money"
    )
    
    if paper_mode != st.session_state.broker.paper_trading:
        st.session_state.broker.paper_trading = paper_mode
        st.sidebar.success(f"Mode changed to: {'Paper' if paper_mode else 'Live'} Trading")
    
    st.sidebar.divider()
    
    # Bot controls
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start Bot", 
            disabled=st.session_state.bot_running,
            use_container_width=True
        ):
            if st.session_state.strategy.start():
                st.session_state.bot_running = True
                st.sidebar.success("Bot started!")
            else:
                st.sidebar.error("Failed to start bot. Check credentials.")
    
    with col2:
        if st.button(
            "⏹️ Stop Bot", 
            disabled=not st.session_state.bot_running,
            use_container_width=True
        ):
            st.session_state.strategy.stop()
            st.session_state.bot_running = False
            st.sidebar.info("Bot stopped.")
    
    st.sidebar.divider()
    
    # Connection status
    st.sidebar.subheader("🔗 Connection Status")
    broker_status = st.session_state.broker.connection_status
    if "Connected" in broker_status:
        st.sidebar.success(broker_status)
    else:
        st.sidebar.warning(broker_status)
    
    # Manual reconnect button
    if st.sidebar.button("🔄 Reconnect", use_container_width=True):
        if st.session_state.broker.reconnect():
            st.sidebar.success("Reconnected successfully!")
        else:
            st.sidebar.error("Reconnection failed.")
    
    st.sidebar.divider()
    
    # Market timing info
    st.sidebar.subheader("⏰ Market Timing")
    time_info = TimeManager.get_time_display()
    st.sidebar.text(f"Market Open:  {time_info['market_open']}")
    st.sidebar.text(f"Range End:    {time_info['range_end']}")
    st.sidebar.text(f"Exit Time:    {time_info['exit_time']}")
    st.sidebar.text(f"Market Close: {time_info['market_close']}")
    
    if time_info['is_weekend']:
        st.sidebar.warning("📅 Weekend - Market Closed")
    
    st.sidebar.divider()
    
    # Auto-refresh toggle
    st.session_state.auto_refresh = st.sidebar.checkbox(
        "Auto-refresh (5 sec)", 
        value=st.session_state.auto_refresh
    )
    
    # Strategy parameters (read-only display)
    st.sidebar.subheader("📊 Strategy Parameters")
    st.sidebar.text("Symbol: RELIANCE-EQ (NSE)")
    st.sidebar.text("Position Size: 1 share")
    st.sidebar.text("Leverage: ~5x (Intraday)")
    st.sidebar.text("Stop Loss: None")


def render_main_dashboard():
    """Render main dashboard with strategy state."""
    # Get current state
    state = st.session_state.strategy.get_state_summary()
    
    # Top row - Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Current Price",
            f"₹{state['current_price']:,.2f}" if state['current_price'] else "N/A",
            help="Last traded price of Reliance Industries"
        )
    
    with col2:
        st.metric(
            "📈 Range High",
            f"₹{state['range_high']:,.2f}" if state['range_high'] else "Building...",
            help="Opening range high (9:15 AM - 11:15 AM)"
        )
    
    with col3:
        st.metric(
            "📉 Range Low",
            f"₹{state['range_low']:,.2f}" if state['range_low'] else "Building...",
            help="Opening range low (9:15 AM - 11:15 AM)"
        )
    
    with col4:
        state_emoji = get_state_color(state['strategy_state'])
        st.metric(
            "🎯 Strategy State",
            f"{state_emoji} {state['strategy_state']}",
            help="Current state of the trading strategy"
        )
    
    st.divider()
    
    # Second row - Position info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pos_emoji = get_position_color(state['position'])
        st.metric(
            "📍 Current Position",
            f"{pos_emoji} {state['position']}",
            help="Current position type (LONG/SHORT/NONE)"
        )
    
    with col2:
        st.metric(
            "💰 Entry Price",
            f"₹{state['entry_price']:,.2f}" if state['entry_price'] > 0 else "N/A",
            help="Price at which position was entered"
        )
    
    with col3:
        unrealized_pnl = state['unrealized_pnl']
        delta_color = "normal" if unrealized_pnl >= 0 else "inverse"
        st.metric(
            "📊 Unrealized PnL",
            f"₹{unrealized_pnl:,.2f}",
            delta=f"₹{unrealized_pnl:,.2f}" if state['position'] != 'NONE' else None,
            delta_color=delta_color if unrealized_pnl != 0 else "off",
            help="Current unrealized profit/loss"
        )
    
    with col4:
        realized_pnl = state['realized_pnl']
        st.metric(
            "✅ Realized PnL",
            f"₹{realized_pnl:,.2f}",
            help="Total realized profit/loss for the day"
        )
    
    st.divider()
    
    # Status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if state['is_running']:
            st.success("🟢 Bot is RUNNING")
        else:
            st.warning("🟡 Bot is STOPPED")
    
    with col2:
        if state['trade_taken_today']:
            st.info("✅ Trade taken today")
        else:
            st.info("⏳ Waiting for trade signal")
    
    with col3:
        if state['range_complete']:
            st.success("📊 Range Complete")
        else:
            st.warning("📊 Building Range...")
    
    # Error message if any
    if state['error_message']:
        st.error(f"⚠️ Error: {state['error_message']}")
    
    # Last update time
    if state['last_update']:
        st.caption(f"Last updated: {state['last_update']}")


def render_trade_log():
    """Render trade history table."""
    st.subheader("📝 Trade Log")
    
    # Read from CSV file
    trades_file = "logs/trades.csv"
    
    if os.path.exists(trades_file):
        try:
            df = pd.read_csv(trades_file)
            
            if not df.empty:
                # Format the dataframe
                df['price'] = df['price'].apply(lambda x: f"₹{x:,.2f}")
                df['pnl'] = df['pnl'].apply(lambda x: f"₹{x:,.2f}")
                
                # Display most recent trades first
                st.dataframe(
                    df.iloc[::-1],  # Reverse order
                    use_container_width=True,
                    hide_index=True
                )
                
                # Summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Trades", len(df))
                with col2:
                    # Parse PnL values back to float for calculation
                    pnl_values = df['pnl'].str.replace('₹', '').str.replace(',', '').astype(float)
                    total_pnl = pnl_values.sum()
                    st.metric("Total PnL", f"₹{total_pnl:,.2f}")
                with col3:
                    win_count = (pnl_values > 0).sum()
                    st.metric("Winning Trades", win_count)
            else:
                st.info("No trades recorded yet.")
        except Exception as e:
            st.warning(f"Could not load trade history: {e}")
    else:
        st.info("No trade history available. Trades will appear here once executed.")


def render_range_visualization():
    """Render a simple visualization of price vs range."""
    st.subheader("📊 Price vs Range")
    
    state = st.session_state.strategy.get_state_summary()
    
    if state['range_high'] and state['range_low'] and state['current_price']:
        range_high = state['range_high']
        range_low = state['range_low']
        current_price = state['current_price']
        range_size = range_high - range_low
        
        # Create a simple bar chart representation
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            # Progress bar showing price position within range
            if current_price >= range_high:
                progress = 1.0
                position_text = "🚀 ABOVE RANGE (BREAKOUT)"
            elif current_price <= range_low:
                progress = 0.0
                position_text = "📉 BELOW RANGE (BREAKDOWN)"
            else:
                progress = (current_price - range_low) / range_size
                position_text = f"📊 Within Range ({progress*100:.1f}%)"
            
            st.progress(progress)
            st.text(position_text)
            
            # Display range metrics
            st.text(f"Range Size: ₹{range_size:,.2f} ({range_size/range_low*100:.2f}%)")
            st.text(f"Distance to High: ₹{range_high - current_price:,.2f}")
            st.text(f"Distance to Low: ₹{current_price - range_low:,.2f}")
    else:
        st.info("Range data not available yet. Will display once range is established.")


def main():
    """Main application function."""
    # Initialize session state
    initialize_session_state()
    
    # Render components
    render_header()
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Trade Log", "📈 Range Analysis"])
    
    with tab1:
        render_main_dashboard()
    
    with tab2:
        render_trade_log()
    
    with tab3:
        render_range_visualization()
    
    # Auto-refresh logic
    if st.session_state.auto_refresh and st.session_state.bot_running:
        # Run strategy tick
        current_time = time.time()
        if current_time - st.session_state.last_tick_time >= 5:
            st.session_state.strategy.tick()
            st.session_state.last_tick_time = current_time
        
        # Schedule rerun
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
