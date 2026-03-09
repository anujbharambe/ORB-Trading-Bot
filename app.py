"""
Opening Range Breakout (ORB) Trading Bot - Streamlit Dashboard
Main entry point for the trading application.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
from datetime import timedelta

from strategy.bot_runner import BotRunner
from strategy.orb_strategy import StrategyState, PositionType
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


# ── Session-state initialization ───────────────────────────────────

def _get_runner() -> BotRunner:
    """Return the singleton BotRunner stored in session state."""
    if 'runner' not in st.session_state:
        st.session_state.runner = BotRunner(paper_trading=True)
    return st.session_state.runner


# ── Helper functions ───────────────────────────────────────────────

def get_state_color(state: str) -> str:
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
    if position == 'LONG':
        return '🟢'
    elif position == 'SHORT':
        return '🔴'
    return '⚪'


# ── Sidebar ────────────────────────────────────────────────────────

def render_sidebar():
    runner = _get_runner()

    st.sidebar.header("⚙️ Controls")

    # Trading mode toggle
    paper_mode = st.sidebar.checkbox(
        "Paper Trading Mode",
        value=runner.paper_trading,
        help="When enabled, simulates trades without real money"
    )
    if paper_mode != runner.paper_trading:
        runner.set_paper_trading(paper_mode)
        st.sidebar.success(f"Mode changed to: {'Paper' if paper_mode else 'Live'} Trading")

    st.sidebar.divider()

    # Bot controls
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("▶️ Start Bot", disabled=runner.is_running, use_container_width=True):
            if runner.start():
                st.sidebar.success("Bot started!")
            else:
                st.sidebar.error("Failed to start bot. Check credentials.")
    with col2:
        if st.button("⏹️ Stop Bot", disabled=not runner.is_running, use_container_width=True):
            runner.stop()
            st.sidebar.info("Bot stopped.")

    st.sidebar.divider()

    # Connection status
    st.sidebar.subheader("🔗 Connection Status")
    broker_status = runner.connection_status
    if "Connected" in broker_status:
        st.sidebar.success(broker_status)
    else:
        st.sidebar.warning(broker_status)

    if st.sidebar.button("🔄 Reconnect", use_container_width=True):
        if runner.broker.reconnect():
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

    # Strategy parameters (read-only display)
    st.sidebar.subheader("📊 Strategy Parameters")
    st.sidebar.text("Symbol: RELIANCE-EQ (NSE)")
    st.sidebar.text("Position Size: 1 share")
    st.sidebar.text("Leverage: ~5x (Intraday)")
    st.sidebar.text("Stop Loss: None")


# ── Auto-refreshing dashboard fragment ─────────────────────────────

@st.fragment(run_every=timedelta(seconds=5))
def live_dashboard():
    """This fragment auto-refreshes every 5 seconds without blocking the
    Streamlit event loop or causing a full page rerun."""
    runner = _get_runner()
    state = runner.get_state()

    # ── Row 1: Key metrics ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "📊 Current Price",
            f"₹{state['current_price']:,.2f}" if state['current_price'] else "N/A",
        )
    with col2:
        st.metric(
            "📈 Range High",
            f"₹{state['range_high']:,.2f}" if state['range_high'] else "Building...",
        )
    with col3:
        st.metric(
            "📉 Range Low",
            f"₹{state['range_low']:,.2f}" if state['range_low'] else "Building...",
        )
    with col4:
        emoji = get_state_color(state['strategy_state'])
        st.metric("🎯 Strategy State", f"{emoji} {state['strategy_state']}")

    st.divider()

    # ── Row 2: Position info ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pos_emoji = get_position_color(state['position'])
        st.metric("📍 Current Position", f"{pos_emoji} {state['position']}")
    with col2:
        st.metric(
            "💰 Entry Price",
            f"₹{state['entry_price']:,.2f}" if state['entry_price'] > 0 else "N/A",
        )
    with col3:
        u_pnl = state['unrealized_pnl']
        delta_color = "normal" if u_pnl >= 0 else "inverse"
        st.metric(
            "📊 Unrealized PnL",
            f"₹{u_pnl:,.2f}",
            delta=f"₹{u_pnl:,.2f}" if state['position'] != 'NONE' else None,
            delta_color=delta_color if u_pnl != 0 else "off",
        )
    with col4:
        st.metric("✅ Realized PnL", f"₹{state['realized_pnl']:,.2f}")

    st.divider()

    # ── Status indicators ──
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

    if state['error_message']:
        st.error(f"⚠️ Error: {state['error_message']}")
    if state['last_update']:
        st.caption(f"Last updated: {state['last_update']}")


# ── Trade log (also auto-refreshes) ───────────────────────────────

@st.fragment(run_every=timedelta(seconds=10))
def trade_log_fragment():
    st.subheader("📝 Trade Log")
    trades_file = "logs/trades.csv"
    if os.path.exists(trades_file):
        try:
            df = pd.read_csv(trades_file)
            if not df.empty:
                display_df = df.copy()
                display_df['price'] = display_df['price'].apply(lambda x: f"₹{x:,.2f}")
                display_df['pnl'] = display_df['pnl'].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)

                pnl_vals = df['pnl'].astype(float)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Total Trades", len(df))
                with c2:
                    st.metric("Total PnL", f"₹{pnl_vals.sum():,.2f}")
                with c3:
                    st.metric("Winning Trades", int((pnl_vals > 0).sum()))
            else:
                st.info("No trades recorded yet.")
        except Exception as e:
            st.warning(f"Could not load trade history: {e}")
    else:
        st.info("No trade history available. Trades will appear here once executed.")


# ── Range visualization (also auto-refreshes) ─────────────────────

@st.fragment(run_every=timedelta(seconds=5))
def range_visualization_fragment():
    st.subheader("📊 Price vs Range")
    state = _get_runner().get_state()

    if state['range_high'] and state['range_low'] and state['current_price']:
        rh, rl, cp = state['range_high'], state['range_low'], state['current_price']
        rs = rh - rl

        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            if cp >= rh:
                progress = 1.0
                label = "🚀 ABOVE RANGE (BREAKOUT)"
            elif cp <= rl:
                progress = 0.0
                label = "📉 BELOW RANGE (BREAKDOWN)"
            else:
                progress = (cp - rl) / rs
                label = f"📊 Within Range ({progress * 100:.1f}%)"

            st.progress(progress)
            st.text(label)
            st.text(f"Range Size: ₹{rs:,.2f} ({rs / rl * 100:.2f}%)")
            st.text(f"Distance to High: ₹{rh - cp:,.2f}")
            st.text(f"Distance to Low: ₹{cp - rl:,.2f}")
    else:
        st.info("Range data not available yet. Will display once range is established.")


# ── Main ───────────────────────────────────────────────────────────

def main():
    runner = _get_runner()

    # Header
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        st.title("📈 ORB Trading Bot")
        st.caption("Opening Range Breakout Strategy - Reliance Industries (NSE)")
    with col3:
        ti = TimeManager.get_time_display()
        st.metric("Current Time (IST)", ti['current_time'].split(' ')[1])

    render_sidebar()

    # Tabs with auto-refreshing fragments — no time.sleep, no st.rerun
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Trade Log", "📈 Range Analysis"])
    with tab1:
        live_dashboard()
    with tab2:
        trade_log_fragment()
    with tab3:
        range_visualization_fragment()


if __name__ == "__main__":
    main()
