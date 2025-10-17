#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

try:  # pragma: no cover
    import pandas as pd  # noqa: F401
except ModuleNotFoundError as exc:
    raise SystemExit("pandas is required to run the optimizer") from exc

from src.data_loader import download_prices_if_needed
from src.optimizer import run_optimization
from src.utils import dump_json, ensure_parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optuna optimization for grid strategy")
    parser.add_argument("--data", type=Path, required=True, help="Path to OHLCV CSV data")
    parser.add_argument("--trials", type=int, default=10, help="Number of trials")
    parser.add_argument("--study-name", type=str, default="grid", help="Optuna study name")
    parser.add_argument("--storage", type=str, default="sqlite:///results/optuna.db", help="Optuna storage URL")
    parser.add_argument("--jobs", type=int, default=1, help="Parallel jobs")
    parser.add_argument("--update-prices", action="store_true", help="Download data if missing")
    parser.add_argument("--symbol", type=str, default="bitcoin", help="CoinGecko symbol")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.update_prices:
        download_prices_if_needed(args.data, symbol=args.symbol)
    study = run_optimization(args.data, n_trials=args.trials, study_name=args.study_name, storage=args.storage, n_jobs=args.jobs)
    best_payload = {"best_params": study.best_params, "best_value": study.best_value}
    output_json = Path("results/optuna_best.json")
    ensure_parent(output_json)
    dump_json(output_json, best_payload)
    print("Best final_btc", -study.best_value)


if __name__ == "__main__":
    main()
