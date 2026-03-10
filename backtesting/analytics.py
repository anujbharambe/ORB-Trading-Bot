"""
Analytics Module for ORB Backtesting
Computes performance metrics and generates charts / reports.
"""

import logging
import os
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for chart generation
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from backtesting.engine import BacktestResult

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Metrics
# ═══════════════════════════════════════════════════════════════════


def compute_metrics(result: BacktestResult) -> Dict[str, Any]:
    """
    Compute comprehensive performance metrics from a backtest result.

    Returns a flat dict suitable for display and serialisation.
    """
    trades = result.trades
    equity_df = result.daily_equity
    cfg = result.config

    metrics: Dict[str, Any] = {}

    # ── Return metrics ─────────────────────────────────────────────
    initial = cfg.initial_capital
    final = equity_df["equity"].iloc[-1] if not equity_df.empty else initial
    total_pnl = final - initial
    total_return_pct = (total_pnl / initial) * 100.0 if initial else 0.0

    n_days = len(equity_df)
    n_years = n_days / 252.0 if n_days else 0.0
    cagr = ((final / initial) ** (1.0 / n_years) - 1.0) * 100.0 if n_years > 0 and initial > 0 else 0.0

    metrics["initial_capital"] = initial
    metrics["final_equity"] = round(final, 2)
    metrics["total_pnl"] = round(total_pnl, 2)
    metrics["total_return_pct"] = round(total_return_pct, 2)
    metrics["cagr_pct"] = round(cagr, 2)
    metrics["n_trading_days"] = n_days
    metrics["n_years"] = round(n_years, 2)

    # ── Drawdown metrics ───────────────────────────────────────────
    if not equity_df.empty:
        eq = equity_df["equity"]
        running_max = eq.cummax()
        drawdown = (eq - running_max) / running_max * 100.0
        max_dd = drawdown.min()

        # Max drawdown duration (in trading days)
        is_dd = eq < running_max
        dd_groups = (~is_dd).cumsum()
        dd_durations = is_dd.groupby(dd_groups).sum()
        max_dd_duration = int(dd_durations.max()) if not dd_durations.empty else 0
        avg_dd = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0.0
    else:
        max_dd = 0.0
        max_dd_duration = 0
        avg_dd = 0.0

    metrics["max_drawdown_pct"] = round(max_dd, 2)
    metrics["max_drawdown_duration_days"] = max_dd_duration
    metrics["avg_drawdown_pct"] = round(avg_dd, 2)

    # ── Risk-adjusted ratios ───────────────────────────────────────
    if not equity_df.empty and len(equity_df) > 1:
        daily_returns = equity_df["equity"].pct_change().dropna()
        mean_ret = daily_returns.mean()
        std_ret = daily_returns.std()

        # Sharpe (annualised, risk-free = 0 for simplicity)
        sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0.0

        # Sortino (downside deviation)
        downside = daily_returns[daily_returns < 0]
        down_std = downside.std() if len(downside) > 0 else 0.0
        sortino = (mean_ret / down_std) * np.sqrt(252) if down_std > 0 else 0.0

        # Calmar
        calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0.0
    else:
        sharpe = sortino = calmar = 0.0

    metrics["sharpe_ratio"] = round(sharpe, 3)
    metrics["sortino_ratio"] = round(sortino, 3)
    metrics["calmar_ratio"] = round(calmar, 3)

    # ── Trade statistics ───────────────────────────────────────────
    n_trades = len(trades)
    metrics["total_trades"] = n_trades

    if n_trades > 0:
        pnls = [t["net_pnl"] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        metrics["win_rate_pct"] = round(len(wins) / n_trades * 100.0, 2)
        metrics["avg_win"] = round(np.mean(wins), 2) if wins else 0.0
        metrics["avg_loss"] = round(np.mean(losses), 2) if losses else 0.0
        metrics["largest_win"] = round(max(pnls), 2)
        metrics["largest_loss"] = round(min(pnls), 2)
        metrics["avg_trade_pnl"] = round(np.mean(pnls), 2)

        # Profit factor
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        metrics["profit_factor"] = (
            round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf")
        )
        metrics["gross_profit"] = round(gross_profit, 2)
        metrics["gross_loss"] = round(-gross_loss, 2)

        # Consecutive wins / losses
        metrics["max_consecutive_wins"] = _max_consecutive(pnls, positive=True)
        metrics["max_consecutive_losses"] = _max_consecutive(pnls, positive=False)

        # Direction split
        longs = [t for t in trades if t["direction"] == "LONG"]
        shorts = [t for t in trades if t["direction"] == "SHORT"]
        metrics["long_trades"] = len(longs)
        metrics["short_trades"] = len(shorts)

        # Exposure
        metrics["trade_days_pct"] = round(n_trades / n_days * 100.0, 2) if n_days else 0.0
        metrics["trades_per_year"] = round(n_trades / n_years, 1) if n_years else 0.0

        # Total commissions
        metrics["total_commission"] = round(sum(t["commission"] for t in trades), 2)
    else:
        for k in [
            "win_rate_pct", "avg_win", "avg_loss", "largest_win", "largest_loss",
            "avg_trade_pnl", "profit_factor", "gross_profit", "gross_loss",
            "max_consecutive_wins", "max_consecutive_losses", "long_trades",
            "short_trades", "trade_days_pct", "trades_per_year", "total_commission",
        ]:
            metrics[k] = 0

    # ── Monthly / Yearly returns ───────────────────────────────────
    metrics["monthly_returns"] = _monthly_returns(trades, cfg.initial_capital, equity_df)
    metrics["yearly_returns"] = _yearly_returns(trades, cfg.initial_capital, equity_df)

    return metrics


# ═══════════════════════════════════════════════════════════════════
#  Report generation
# ═══════════════════════════════════════════════════════════════════


def generate_report(
    result: BacktestResult,
    metrics: Dict[str, Any],
    output_dir: str,
) -> None:
    """
    Save a full backtest report to *output_dir*:
      - report.txt          (text summary)
      - trades.csv          (trade log)
      - equity_curve.png
      - drawdown.png
      - monthly_returns.png
      - yearly_returns.png
      - trade_distribution.png
    """
    os.makedirs(output_dir, exist_ok=True)

    _write_text_report(metrics, result, output_dir)
    _write_trades_csv(result.trades, output_dir)
    _plot_equity_curve(result.daily_equity, output_dir)
    _plot_drawdown(result.daily_equity, output_dir)
    _plot_monthly_returns(metrics.get("monthly_returns", {}), output_dir)
    _plot_yearly_returns(metrics.get("yearly_returns", {}), output_dir)
    _plot_trade_distribution(result.trades, output_dir)

    logger.info(f"Report saved to {output_dir}")


# ═══════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════


def _max_consecutive(pnls: List[float], positive: bool) -> int:
    """Return the longest streak of positive (or non-positive) PnL values."""
    best = current = 0
    for p in pnls:
        if (positive and p > 0) or (not positive and p <= 0):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _monthly_returns(
    trades: List[Dict], initial_capital: float, equity_df: pd.DataFrame
) -> Dict[str, Dict[str, float]]:
    """
    Compute monthly return percentages.

    Returns: {year_str: {month_str: return_pct, ...}, ...}
    """
    if equity_df.empty:
        return {}

    eq = equity_df["equity"].copy()
    eq.index = pd.to_datetime(eq.index)

    # End-of-month equity
    monthly_eq = eq.resample("ME").last()

    result: Dict[str, Dict[str, float]] = {}
    prev = initial_capital
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    for ts, val in monthly_eq.items():
        yr = str(ts.year)
        mo = month_names[ts.month - 1]
        ret = ((val - prev) / prev) * 100.0 if prev else 0.0
        result.setdefault(yr, {})[mo] = round(ret, 2)
        prev = val

    return result


def _yearly_returns(
    trades: List[Dict], initial_capital: float, equity_df: pd.DataFrame
) -> Dict[str, float]:
    """Compute yearly return percentages."""
    if equity_df.empty:
        return {}

    eq = equity_df["equity"].copy()
    eq.index = pd.to_datetime(eq.index)

    yearly_eq = eq.resample("YE").last()
    result: Dict[str, float] = {}
    prev = initial_capital
    for ts, val in yearly_eq.items():
        ret = ((val - prev) / prev) * 100.0 if prev else 0.0
        result[str(ts.year)] = round(ret, 2)
        prev = val
    return result


# ── Text report ────────────────────────────────────────────────────


def _write_text_report(
    metrics: Dict[str, Any], result: BacktestResult, output_dir: str
) -> None:
    lines = [
        "=" * 60,
        "  ORB Strategy — Backtest Report",
        "=" * 60,
        "",
        f"  Symbol:           {result.config.symbol}",
        f"  Period:           {result.config.start_date or 'all'} → {result.config.end_date or 'all'}",
        f"  Trading days:     {metrics['n_trading_days']}",
        f"  Duration (years): {metrics['n_years']}",
        "",
        "── Returns ─────────────────────────────────────",
        f"  Initial capital:  ₹{metrics['initial_capital']:>14,.2f}",
        f"  Final equity:     ₹{metrics['final_equity']:>14,.2f}",
        f"  Total PnL:        ₹{metrics['total_pnl']:>14,.2f}",
        f"  Total return:       {metrics['total_return_pct']:>12.2f} %",
        f"  CAGR:               {metrics['cagr_pct']:>12.2f} %",
        "",
        "── Risk ────────────────────────────────────────",
        f"  Max drawdown:       {metrics['max_drawdown_pct']:>12.2f} %",
        f"  Max DD duration:    {metrics['max_drawdown_duration_days']:>12} days",
        f"  Avg drawdown:       {metrics['avg_drawdown_pct']:>12.2f} %",
        "",
        "── Ratios ──────────────────────────────────────",
        f"  Sharpe ratio:       {metrics['sharpe_ratio']:>12.3f}",
        f"  Sortino ratio:      {metrics['sortino_ratio']:>12.3f}",
        f"  Calmar ratio:       {metrics['calmar_ratio']:>12.3f}",
        f"  Profit factor:      {metrics['profit_factor']:>12.3f}",
        "",
        "── Trade Statistics ────────────────────────────",
        f"  Total trades:       {metrics['total_trades']:>12}",
        f"  Long trades:        {metrics['long_trades']:>12}",
        f"  Short trades:       {metrics['short_trades']:>12}",
        f"  Win rate:           {metrics['win_rate_pct']:>12.2f} %",
        f"  Avg win:          ₹{metrics['avg_win']:>14,.2f}",
        f"  Avg loss:         ₹{metrics['avg_loss']:>14,.2f}",
        f"  Avg trade PnL:    ₹{metrics['avg_trade_pnl']:>14,.2f}",
        f"  Largest win:      ₹{metrics['largest_win']:>14,.2f}",
        f"  Largest loss:     ₹{metrics['largest_loss']:>14,.2f}",
        f"  Gross profit:     ₹{metrics['gross_profit']:>14,.2f}",
        f"  Gross loss:       ₹{metrics['gross_loss']:>14,.2f}",
        f"  Total commission: ₹{metrics['total_commission']:>14,.2f}",
        f"  Consec. wins:       {metrics['max_consecutive_wins']:>12}",
        f"  Consec. losses:     {metrics['max_consecutive_losses']:>12}",
        "",
        "── Exposure ────────────────────────────────────",
        f"  Trade-day %:        {metrics['trade_days_pct']:>12.2f} %",
        f"  Trades / year:      {metrics['trades_per_year']:>12.1f}",
        "",
        "=" * 60,
    ]

    path = os.path.join(output_dir, "report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Trades CSV ─────────────────────────────────────────────────────


def _write_trades_csv(trades: List[Dict], output_dir: str) -> None:
    if not trades:
        return
    df = pd.DataFrame(trades)
    path = os.path.join(output_dir, "trades.csv")
    df.to_csv(path, index=False)


# ── Charts ─────────────────────────────────────────────────────────


def _plot_equity_curve(equity_df: pd.DataFrame, output_dir: str) -> None:
    if equity_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(equity_df.index, equity_df["equity"], linewidth=1.0, color="#2196F3")
    ax.fill_between(equity_df.index, equity_df["equity"], alpha=0.08, color="#2196F3")
    ax.set_title("Equity Curve", fontsize=14)
    ax.set_ylabel("Equity (₹)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "equity_curve.png"), dpi=150)
    plt.close(fig)


def _plot_drawdown(equity_df: pd.DataFrame, output_dir: str) -> None:
    if equity_df.empty:
        return
    eq = equity_df["equity"]
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max * 100.0

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(equity_df.index, drawdown, 0, alpha=0.45, color="#F44336")
    ax.plot(equity_df.index, drawdown, linewidth=0.7, color="#D32F2F")
    ax.set_title("Drawdown", fontsize=14)
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "drawdown.png"), dpi=150)
    plt.close(fig)


def _plot_monthly_returns(
    monthly: Dict[str, Dict[str, float]], output_dir: str
) -> None:
    if not monthly:
        return

    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    years = sorted(monthly.keys())
    data = []
    for yr in years:
        row = [monthly[yr].get(m, 0.0) for m in months]
        data.append(row)

    arr = np.array(data)
    fig, ax = plt.subplots(figsize=(12, max(4, len(years) * 0.45 + 1)))
    vmax = max(abs(arr.min()), abs(arr.max()), 1)
    cax = ax.imshow(arr, aspect="auto", cmap="RdYlGn", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(12))
    ax.set_xticklabels(months, fontsize=8)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels(years, fontsize=8)
    ax.set_title("Monthly Returns (%)", fontsize=14)

    # Annotate cells
    for i in range(len(years)):
        for j in range(12):
            val = arr[i, j]
            if val != 0:
                ax.text(
                    j, i, f"{val:.1f}",
                    ha="center", va="center", fontsize=6,
                    color="white" if abs(val) > vmax * 0.6 else "black",
                )

    fig.colorbar(cax, ax=ax, shrink=0.6, label="%")
    fig.savefig(os.path.join(output_dir, "monthly_returns.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_yearly_returns(yearly: Dict[str, float], output_dir: str) -> None:
    if not yearly:
        return

    years = sorted(yearly.keys())
    vals = [yearly[y] for y in years]
    colors = ["#4CAF50" if v >= 0 else "#F44336" for v in vals]

    fig, ax = plt.subplots(figsize=(max(8, len(years) * 0.7), 5))
    bars = ax.bar(range(len(years)), vals, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=8)
    ax.set_title("Yearly Returns (%)", fontsize=14)
    ax.set_ylabel("Return (%)")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.grid(True, axis="y", alpha=0.3)

    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (0.3 if v >= 0 else -0.8),
            f"{v:.1f}%",
            ha="center", va="bottom" if v >= 0 else "top",
            fontsize=7,
        )

    fig.savefig(os.path.join(output_dir, "yearly_returns.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_trade_distribution(trades: List[Dict], output_dir: str) -> None:
    if not trades:
        return

    pnls = [t["net_pnl"] for t in trades]
    fig, ax = plt.subplots(figsize=(10, 5))
    n_bins = min(80, max(20, len(pnls) // 10))
    ax.hist(pnls, bins=n_bins, color="#2196F3", edgecolor="white", linewidth=0.5, alpha=0.85)
    ax.axvline(0, color="red", linewidth=1, linestyle="--")
    ax.axvline(np.mean(pnls), color="orange", linewidth=1, linestyle="--", label=f"Mean: ₹{np.mean(pnls):,.2f}")
    ax.set_title("Trade PnL Distribution", fontsize=14)
    ax.set_xlabel("PnL (₹)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "trade_distribution.png"), dpi=150)
    plt.close(fig)
