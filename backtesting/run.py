"""
CLI entry point for the ORB backtesting engine.

Usage:
    python -m backtesting --symbol RELIANCE-EQ
    python -m backtesting --symbol RELIANCE-EQ --start 2020-01-01 --end 2024-12-31
    python -m backtesting --csv data/RELIANCE_5minute.csv --capital 200000
"""

import argparse
import logging
from datetime import date, datetime

from backtesting.engine import BacktestConfig, BacktestEngine
from backtesting.analytics import compute_metrics, generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ORB Strategy Backtester — replay 5-minute candle data",
    )
    p.add_argument(
        "--symbol", default="RELIANCE-EQ",
        help="Trading symbol (default: RELIANCE-EQ). "
             "Used to auto-resolve CSV path: data/{SYMBOL}_5minute.csv",
    )
    p.add_argument(
        "--csv", default="",
        help="Explicit path to 5-minute candle CSV. Overrides --symbol path resolution.",
    )
    p.add_argument("--start", type=_parse_date, default=None, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", type=_parse_date, default=None, help="End date (YYYY-MM-DD)")
    p.add_argument("--capital", type=float, default=100_000, help="Initial capital (default: 100000)")
    p.add_argument(
        "--sizing-mode", default="fixed_quantity",
        choices=["fixed_quantity", "fixed_capital", "percent_of_capital"],
        help="Position sizing mode (default: fixed_quantity)",
    )
    p.add_argument("--quantity", type=int, default=1, help="Fixed quantity (default: 1)")
    p.add_argument("--fixed-capital", type=float, default=10_000, help="Fixed capital per trade (default: 10000)")
    p.add_argument("--pct-capital", type=float, default=5.0, help="Percent of capital per trade (default: 5.0)")
    p.add_argument("--leverage", type=float, default=5.0, help="Leverage multiplier (default: 5.0)")
    p.add_argument("--commission", type=float, default=0.05, help="Commission %% (default: 0.05)")
    p.add_argument("--slippage", type=float, default=0.05, help="Slippage %% per side (default: 0.05)")
    p.add_argument("--output", default="backtesting_results", help="Output directory (default: backtesting_results/)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    config = BacktestConfig(
        symbol=args.symbol,
        csv_path=args.csv,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        position_sizing_mode=args.sizing_mode,
        fixed_quantity=args.quantity,
        fixed_capital=args.fixed_capital,
        percent_of_capital=args.pct_capital,
        leverage=args.leverage,
        commission_pct=args.commission,
        slippage_pct=args.slippage,
    )

    print()
    print("=" * 60)
    print("  ORB Strategy Backtester")
    print("=" * 60)
    print(f"  Symbol:     {config.symbol}")
    print(f"  Capital:    Rs.{config.initial_capital:,.0f}")
    print(f"  Sizing:     {config.position_sizing_mode}")
    print(f"  Leverage:   {config.leverage}x")
    print(f"  Commission: {config.commission_pct}%")
    print(f"  Slippage:   {config.slippage_pct}%")
    print(f"  Date range: {config.start_date or 'all'} -> {config.end_date or 'all'}")
    print("=" * 60)
    print()

    # Run backtest
    engine = BacktestEngine(config)
    result = engine.run()

    # Compute metrics
    metrics = compute_metrics(result)

    # Print summary
    _print_summary(metrics)

    # Save report
    generate_report(result, metrics, args.output)
    print(f"\nFull report saved to: {args.output}/")


def _print_summary(m):
    print()
    print("-- Summary " + "-" * 39)
    print(f"  Total trades:     {m['total_trades']}")
    print(f"  Win rate:         {m['win_rate_pct']}%")
    print(f"  Total PnL:        Rs.{m['total_pnl']:,.2f}")
    print(f"  Total return:     {m['total_return_pct']:.2f}%")
    print(f"  CAGR:             {m['cagr_pct']:.2f}%")
    print(f"  Sharpe ratio:     {m['sharpe_ratio']:.3f}")
    print(f"  Sortino ratio:    {m['sortino_ratio']:.3f}")
    print(f"  Max drawdown:     {m['max_drawdown_pct']:.2f}%")
    print(f"  Profit factor:    {m['profit_factor']:.3f}")
    print(f"  Avg trade PnL:    Rs.{m['avg_trade_pnl']:,.2f}")
    print(f"  Final equity:     Rs.{m['final_equity']:,.2f}")
    print("-" * 50)


if __name__ == "__main__":
    main()
