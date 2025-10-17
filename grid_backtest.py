#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path

try:
    import pandas as pd  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("pandas is required to run the backtest CLI") from exc

from src.backtester import BacktestConfig, GridBacktester
from src.data_loader import download_prices_if_needed, load_price_data
from src.utils import dump_json, ensure_parent, set_random_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run grid accumulation backtest")
    parser.add_argument("--data", type=Path, required=True, help="Path to OHLCV CSV data")
    parser.add_argument("--initial-btc", type=float, default=0.1, help="Initial BTC holdings")
    parser.add_argument("--allocation", type=float, default=50.0, help="USD allocation per buy")
    parser.add_argument("--min-trade-usd", type=float, default=10.0, help="Minimum USD per trade")
    parser.add_argument("--min-trade-btc", type=float, default=1e-5, help="Minimum BTC per trade")
    parser.add_argument("--fee-pct", type=float, default=0.001, help="Exchange fee percentage")
    parser.add_argument("--slippage-pct", type=float, default=0.0005, help="Slippage percentage")
    parser.add_argument("--num-levels", type=int, default=15, help="Number of grid levels")
    parser.add_argument("--take-profit", type=float, default=0.05, help="Take profit percentage")
    parser.add_argument("--stop-loss", type=float, default=0.2, help="Stop loss percentage")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--block-size", type=int, default=1440, help="Processing block size")
    parser.add_argument("--update-prices", action="store_true", help="Download data if missing")
    parser.add_argument("--symbol", type=str, default="bitcoin", help="CoinGecko symbol for live download")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_random_seed(args.seed)
    if args.update_prices:
        download_prices_if_needed(args.data, symbol=args.symbol)
    quality = load_price_data(args.data)
    data = quality.data

    median_price = float(data["close"].median())
    max_price = float(data["close"].max())

    config = BacktestConfig(
        min_price=0.9 * median_price,
        max_price=1.1 * max_price,
        num_levels=args.num_levels,
        allocation_per_buy_usd=args.allocation,
        fee_pct=args.fee_pct,
        slippage_pct=args.slippage_pct,
        initial_btc=args.initial_btc,
        min_trade_btc=args.min_trade_btc,
        min_trade_usd=args.min_trade_usd,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss,
        block_size=args.block_size,
    )

    backtester = GridBacktester(data, config)
    result = backtester.run({
        "missing_pct": quality.quality.missing_pct,
        "zero_volume_pct": quality.quality.zero_volume_pct,
        "adjustments": quality.quality.adjustments,
    })

    summary = {
        "final_btc": result.final_btc,
        "final_usd": result.final_usd,
        "pct_return_btc": result.pct_return_btc,
        "n_trades": result.n_trades,
        "max_drawdown": result.max_drawdown,
        "volatility_est": result.volatility_est,
        "sharpe_approx": result.sharpe_approx,
        "trade_limit_violations": result.trade_limit_violations,
        "paths": {
            "equity_curve": str(result.equity_curve_path),
            "trades": str(result.trades_path),
            "figure": str(result.figure_path),
            "metrics": str(result.metrics_path),
        },
    }
    output_json = Path("results/backtest.json")
    output_csv = Path("results/events.csv")
    ensure_parent(output_json)
    dump_json(output_json, summary)
    if result.trades_path.exists():
        output_csv.write_text(result.trades_path.read_text())

    print("final_btc", result.final_btc)
    print("pct_return_btc", result.pct_return_btc)


if __name__ == "__main__":
    main()
