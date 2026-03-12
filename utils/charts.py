"""
Shared Plotly Chart Functions
Reusable rendering functions for both the backtesting and live performance dashboards.
"""

from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ── Helper ─────────────────────────────────────────────────────────


def kv_table(data: dict):
    """Render a key-value table in Streamlit."""
    df = pd.DataFrame(list(data.items()), columns=["Metric", "Value"])
    st.dataframe(df, hide_index=True, use_container_width=True)


# ── Summary ────────────────────────────────────────────────────────


def render_summary(metrics: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return", f"{metrics['total_return_pct']:.2f}%")
    c2.metric("CAGR", f"{metrics['cagr_pct']:.2f}%")
    c3.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
    c4.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### Returns")
        kv_table({
            "Initial Capital": f"₹{metrics['initial_capital']:,.2f}",
            "Final Equity": f"₹{metrics['final_equity']:,.2f}",
            "Total PnL": f"₹{metrics['total_pnl']:,.2f}",
            "Total Return": f"{metrics['total_return_pct']:.2f}%",
            "CAGR": f"{metrics['cagr_pct']:.2f}%",
        })

        st.markdown("##### Risk")
        kv_table({
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
            "Max DD Duration": f"{metrics['max_drawdown_duration_days']} days",
            "Avg Drawdown": f"{metrics['avg_drawdown_pct']:.2f}%",
        })

        st.markdown("##### Ratios")
        kv_table({
            "Sharpe": f"{metrics['sharpe_ratio']:.3f}",
            "Sortino": f"{metrics['sortino_ratio']:.3f}",
            "Calmar": f"{metrics['calmar_ratio']:.3f}",
            "Profit Factor": f"{metrics['profit_factor']:.3f}",
        })

    with col_right:
        st.markdown("##### Trade Statistics")
        kv_table({
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

        st.markdown("##### Stop-Loss")
        kv_table({
            "SL Exits": metrics.get("stop_loss_count", 0),
            "SL Exit %": f"{metrics.get('stop_loss_pct', 0):.2f}%",
            "EOD Exits": metrics.get("eod_exit_count", 0),
            "Avg PnL (SL)": f"₹{metrics.get('avg_pnl_stop_loss', 0):,.2f}",
            "Avg PnL (EOD)": f"₹{metrics.get('avg_pnl_eod_exit', 0):,.2f}",
            "Win Rate (SL)": f"{metrics.get('win_rate_stop_loss', 0):.2f}%",
            "Win Rate (EOD)": f"{metrics.get('win_rate_eod_exit', 0):.2f}%",
        })

        st.markdown("##### Exposure")
        kv_table({
            "Trade-Day %": f"{metrics['trade_days_pct']:.2f}%",
            "Trades / Year": f"{metrics['trades_per_year']:.1f}",
            "Trading Days": metrics["n_trading_days"],
            "Years": f"{metrics['n_years']:.2f}",
        })


# ── Equity Curve ───────────────────────────────────────────────────


def render_equity_curve(equity_df: pd.DataFrame):
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


# ── Drawdown ───────────────────────────────────────────────────────


def render_drawdown(equity_df: pd.DataFrame):
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


# ── Monthly Returns Heatmap ────────────────────────────────────────


def render_monthly_returns(monthly: dict):
    if not monthly:
        st.info("No monthly data available.")
        return

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    years = sorted(monthly.keys())
    data = [[monthly[yr].get(m, 0.0) for m in months] for yr in years]

    df = pd.DataFrame(data, index=years, columns=months)

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

    with st.expander("View as table"):
        styled = df.style.format("{:.2f}%").background_gradient(
            cmap="RdYlGn", axis=None, vmin=-df.abs().max().max(), vmax=df.abs().max().max()
        )
        st.dataframe(styled, use_container_width=True)


# ── Yearly Returns Bar Chart ──────────────────────────────────────


def render_yearly_returns(yearly: dict):
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


# ── Trade Stats ────────────────────────────────────────────────────


def render_trade_stats(trades: list):
    if not trades:
        st.info("No trades to display.")
        return

    pnls = [t["net_pnl"] for t in trades]
    directions = [t["direction"] for t in trades]

    c1, c2 = st.columns(2)

    with c1:
        df_dir = pd.DataFrame({"direction": directions, "pnl": pnls})
        fig = px.box(df_dir, x="direction", y="pnl", color="direction",
                     color_discrete_map={"LONG": "#4CAF50", "SHORT": "#F44336"},
                     title="PnL by Direction")
        fig.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
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


# ── Trade Log Table ────────────────────────────────────────────────


def render_trade_log(trades: list):
    if not trades:
        st.info("No trades to display.")
        return

    df = pd.DataFrame(trades)

    display_df = df.copy()
    for col in ["entry_price", "exit_price", "gross_pnl", "commission", "net_pnl", "range_high", "range_low"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"₹{x:,.2f}")

    if "exit_reason" not in display_df.columns:
        display_df["exit_reason"] = "EOD_EXIT"

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="trades.csv",
        mime="text/csv",
    )


# ── PnL Distribution Histogram ────────────────────────────────────


def render_pnl_distribution(trades: list):
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
