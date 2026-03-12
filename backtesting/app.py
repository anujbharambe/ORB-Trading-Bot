"""
Streamlit Backtesting Dashboard for ORB Strategy.

Run with:  streamlit run backtesting/app.py
"""

import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is on the path so backtesting package imports work
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backtesting.analytics import compute_metrics
from backtesting.engine import BacktestConfig, BacktestEngine
from utils.charts import (
    kv_table as _kv_table,
    render_summary as _render_summary,
    render_equity_curve as _render_equity_curve,
    render_drawdown as _render_drawdown,
    render_monthly_returns as _render_monthly_returns,
    render_yearly_returns as _render_yearly_returns,
    render_trade_stats as _render_trade_stats,
    render_trade_log as _render_trade_log,
    render_pnl_distribution as _render_pnl_distribution,
)

# ── Page config ────────────────────────────────────────────────────

st.set_page_config(
    page_title="ORB Backtester",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    .stMetric { background-color: #1e1e1e; padding: 10px; border-radius: 5px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar — configuration ───────────────────────────────────────


def _sidebar() -> BacktestConfig:
    st.sidebar.header("⚙️ Backtest Configuration")

    symbol = st.sidebar.text_input("Symbol", value="RELIANCE-EQ")
    csv_path = st.sidebar.text_input(
        "CSV path (leave blank to auto-resolve)",
        value="",
        help="Auto-resolved as data/{SYMBOL}_5minute.csv",
    )

    st.sidebar.subheader("📅 Date Range")
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start", value=date(2015, 2, 2))
    end_date = col2.date_input("End", value=date.today())

    st.sidebar.subheader("💰 Capital & Sizing")
    capital = st.sidebar.number_input("Initial Capital (₹)", value=100_000, min_value=1_000, step=10_000)
    sizing_mode = st.sidebar.selectbox(
        "Position Sizing Mode",
        ["fixed_quantity", "fixed_capital", "percent_of_capital"],
    )
    fixed_qty = 1
    fixed_cap = 10_000.0
    pct_cap = 5.0
    if sizing_mode == "fixed_quantity":
        fixed_qty = st.sidebar.number_input("Quantity", value=1, min_value=1)
    elif sizing_mode == "fixed_capital":
        fixed_cap = st.sidebar.number_input("Capital per trade (₹)", value=10_000.0, min_value=100.0, step=1_000.0)
    else:
        pct_cap = st.sidebar.number_input("% of capital", value=5.0, min_value=0.1, max_value=100.0, step=0.5)

    st.sidebar.subheader("⚡ Leverage")
    leverage = st.sidebar.number_input("Leverage (×)", value=5.0, min_value=1.0, max_value=20.0, step=1.0)

    st.sidebar.subheader("📉 Costs")
    commission = st.sidebar.number_input("Commission (%)", value=0.05, min_value=0.0, step=0.01, format="%.3f")
    slippage = st.sidebar.number_input("Slippage (%)", value=0.05, min_value=0.0, step=0.01, format="%.3f")

    st.sidebar.subheader("🛡️ Risk Management")
    stop_loss_enabled = st.sidebar.checkbox(
        "Enable Stop-Loss (opposite side of range)",
        value=True,
        help="LONG → SL at range low. SHORT → SL at range high.",
    )

    return BacktestConfig(
        symbol=symbol,
        csv_path=csv_path,
        start_date=start_date,
        end_date=end_date,
        initial_capital=float(capital),
        position_sizing_mode=sizing_mode,
        fixed_quantity=fixed_qty,
        fixed_capital=fixed_cap,
        percent_of_capital=pct_cap,
        leverage=leverage,
        commission_pct=commission,
        slippage_pct=slippage,
        stop_loss_enabled=stop_loss_enabled,
    )


# ── Tabs ───────────────────────────────────────────────────────────


# ── Main ───────────────────────────────────────────────────────────


def main():
    st.title("📊 ORB Strategy Backtester")
    st.caption("Opening Range Breakout — Historical Performance Analysis")

    config = _sidebar()

    # Run button
    run_clicked = st.sidebar.button("🚀 Run Backtest", use_container_width=True, type="primary")

    if run_clicked:
        with st.spinner("Running backtest — this may take a moment for large datasets..."):
            engine = BacktestEngine(config)
            result = engine.run()
            metrics = compute_metrics(result)

            st.session_state["bt_result"] = result
            st.session_state["bt_metrics"] = metrics

    # Show results if available
    if "bt_result" not in st.session_state:
        st.info("Configure parameters in the sidebar and click **Run Backtest** to begin.")
        return

    result = st.session_state["bt_result"]
    metrics = st.session_state["bt_metrics"]

    tabs = st.tabs([
        "📋 Summary",
        "📈 Equity Curve",
        "📉 Drawdown",
        "📅 Monthly Returns",
        "📊 Yearly Returns",
        "🎯 Trade Stats",
        "📝 Trade Log",
        "📊 PnL Distribution",
    ])

    with tabs[0]:
        _render_summary(metrics)
    with tabs[1]:
        _render_equity_curve(result.daily_equity)
    with tabs[2]:
        _render_drawdown(result.daily_equity)
    with tabs[3]:
        _render_monthly_returns(metrics.get("monthly_returns", {}))
    with tabs[4]:
        _render_yearly_returns(metrics.get("yearly_returns", {}))
    with tabs[5]:
        _render_trade_stats(result.trades)
    with tabs[6]:
        _render_trade_log(result.trades)
    with tabs[7]:
        _render_pnl_distribution(result.trades)


if __name__ == "__main__":
    main()
