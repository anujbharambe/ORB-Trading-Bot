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
    )


# ── Tabs ───────────────────────────────────────────────────────────


def _render_summary(metrics: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return", f"{metrics['total_return_pct']:.2f}%")
    c2.metric("CAGR", f"{metrics['cagr_pct']:.2f}%")
    c3.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
    c4.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### Returns")
        _kv_table({
            "Initial Capital": f"₹{metrics['initial_capital']:,.2f}",
            "Final Equity": f"₹{metrics['final_equity']:,.2f}",
            "Total PnL": f"₹{metrics['total_pnl']:,.2f}",
            "Total Return": f"{metrics['total_return_pct']:.2f}%",
            "CAGR": f"{metrics['cagr_pct']:.2f}%",
        })

        st.markdown("##### Risk")
        _kv_table({
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
            "Max DD Duration": f"{metrics['max_drawdown_duration_days']} days",
            "Avg Drawdown": f"{metrics['avg_drawdown_pct']:.2f}%",
        })

        st.markdown("##### Ratios")
        _kv_table({
            "Sharpe": f"{metrics['sharpe_ratio']:.3f}",
            "Sortino": f"{metrics['sortino_ratio']:.3f}",
            "Calmar": f"{metrics['calmar_ratio']:.3f}",
            "Profit Factor": f"{metrics['profit_factor']:.3f}",
        })

    with col_right:
        st.markdown("##### Trade Statistics")
        _kv_table({
            "Total Trades": metrics["total_trades"],
            "Long Trades": metrics["long_trades"],
            "Short Trades": metrics["short_trades"],
            "Win Rate": f"{metrics['win_rate_pct']:.2f}%",
            "Avg Win": f"₹{metrics['avg_win']:,.2f}",
            "Avg Loss": f"₹{metrics['avg_loss']:,.2f}",
            "Avg Trade PnL": f"₹{metrics['avg_trade_pnl']:,.2f}",
            "Largest Win": f"₹{metrics['largest_win']:,.2f}",
            "Largest Loss": f"₹{metrics['largest_loss']:,.2f}",
            "Gross Profit": f"₹{metrics['gross_profit']:,.2f}",
            "Gross Loss": f"₹{metrics['gross_loss']:,.2f}",
            "Total Commission": f"₹{metrics['total_commission']:,.2f}",
            "Consec. Wins": metrics["max_consecutive_wins"],
            "Consec. Losses": metrics["max_consecutive_losses"],
        })

        st.markdown("##### Exposure")
        _kv_table({
            "Trade-Day %": f"{metrics['trade_days_pct']:.2f}%",
            "Trades / Year": f"{metrics['trades_per_year']:.1f}",
            "Trading Days": metrics["n_trading_days"],
            "Years": f"{metrics['n_years']:.2f}",
        })


def _kv_table(data: dict):
    df = pd.DataFrame(list(data.items()), columns=["Metric", "Value"])
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_equity_curve(equity_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df.index,
        y=equity_df["equity"],
        mode="lines",
        line=dict(color="#2196F3", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(33,150,243,0.07)",
        name="Equity",
    ))
    fig.update_layout(
        title="Equity Curve",
        yaxis_title="Equity (₹)",
        xaxis_title="Date",
        hovermode="x unified",
        template="plotly_dark",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_drawdown(equity_df: pd.DataFrame):
    eq = equity_df["equity"]
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max * 100.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df.index,
        y=drawdown,
        mode="lines",
        line=dict(color="#F44336", width=1),
        fill="tozeroy",
        fillcolor="rgba(244,67,54,0.25)",
        name="Drawdown %",
    ))
    fig.update_layout(
        title="Drawdown",
        yaxis_title="Drawdown (%)",
        xaxis_title="Date",
        hovermode="x unified",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_monthly_returns(monthly: dict):
    if not monthly:
        st.info("No monthly data available.")
        return

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    years = sorted(monthly.keys())
    data = [[monthly[yr].get(m, 0.0) for m in months] for yr in years]

    df = pd.DataFrame(data, index=years, columns=months)

    # Interactive heatmap
    fig = px.imshow(
        df.values,
        x=months,
        y=[str(y) for y in years],
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        text_auto=".1f",
        aspect="auto",
        labels=dict(color="Return (%)"),
    )
    fig.update_layout(
        title="Monthly Returns (%)",
        template="plotly_dark",
        height=max(300, len(years) * 35),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Also show as table
    with st.expander("View as table"):
        styled = df.style.format("{:.2f}%").background_gradient(
            cmap="RdYlGn", axis=None, vmin=-df.abs().max().max(), vmax=df.abs().max().max()
        )
        st.dataframe(styled, use_container_width=True)


def _render_yearly_returns(yearly: dict):
    if not yearly:
        st.info("No yearly data available.")
        return

    years = sorted(yearly.keys())
    vals = [yearly[y] for y in years]
    colors = ["#4CAF50" if v >= 0 else "#F44336" for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in years],
        y=vals,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in vals],
        textposition="outside",
    ))
    fig.update_layout(
        title="Yearly Returns (%)",
        yaxis_title="Return (%)",
        template="plotly_dark",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_trade_stats(trades: list):
    if not trades:
        st.info("No trades to display.")
        return

    pnls = [t["net_pnl"] for t in trades]
    directions = [t["direction"] for t in trades]

    c1, c2 = st.columns(2)

    with c1:
        # PnL by direction
        df_dir = pd.DataFrame({"direction": directions, "pnl": pnls})
        fig = px.box(df_dir, x="direction", y="pnl", color="direction",
                     color_discrete_map={"LONG": "#4CAF50", "SHORT": "#F44336"},
                     title="PnL by Direction")
        fig.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Cumulative PnL over trades
        cum_pnl = np.cumsum(pnls)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=cum_pnl, mode="lines",
            line=dict(color="#2196F3"),
            name="Cumulative PnL",
        ))
        fig.update_layout(
            title="Cumulative Trade PnL",
            yaxis_title="Cumulative PnL (₹)",
            xaxis_title="Trade #",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Trades per year
    trade_years = [str(t["date"].year) if isinstance(t["date"], date) else str(t["date"])[:4] for t in trades]
    year_counts = pd.Series(trade_years).value_counts().sort_index()
    fig = px.bar(
        x=year_counts.index, y=year_counts.values,
        labels={"x": "Year", "y": "Trades"},
        title="Trades per Year",
    )
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)


def _render_trade_log(trades: list):
    if not trades:
        st.info("No trades to display.")
        return

    df = pd.DataFrame(trades)

    # Format display columns
    display_df = df.copy()
    for col in ["entry_price", "exit_price", "gross_pnl", "commission", "net_pnl", "range_high", "range_low"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="backtest_trades.csv",
        mime="text/csv",
    )


def _render_pnl_distribution(trades: list):
    if not trades:
        st.info("No trades to display.")
        return

    pnls = [t["net_pnl"] for t in trades]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=pnls,
        nbinsx=min(80, max(20, len(pnls) // 10)),
        marker_color="#2196F3",
        opacity=0.85,
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="red")
    fig.add_vline(x=np.mean(pnls), line_dash="dash", line_color="orange",
                  annotation_text=f"Mean: ₹{np.mean(pnls):,.2f}")
    fig.update_layout(
        title="Trade PnL Distribution",
        xaxis_title="PnL (₹)",
        yaxis_title="Frequency",
        template="plotly_dark",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


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
