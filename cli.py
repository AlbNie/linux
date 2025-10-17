#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:  # pragma: no cover
    import pandas as pd  # noqa: F401
except ModuleNotFoundError as exc:
    raise SystemExit("pandas is required for the interactive CLI") from exc

from src.backtester import BacktestConfig, GridBacktester
from src.data_loader import load_price_data
from src.utils import dump_json, ensure_parent, set_random_seed

PROFILES = {
    "conservador": {
        "num_levels": 10,
        "allocation_per_buy_usd": 25.0,
        "take_profit_pct": 0.03,
        "stop_loss_pct": 0.15,
    },
    "equilibrado": {
        "num_levels": 20,
        "allocation_per_buy_usd": 50.0,
        "take_profit_pct": 0.05,
        "stop_loss_pct": 0.2,
    },
    "agresivo": {
        "num_levels": 40,
        "allocation_per_buy_usd": 100.0,
        "take_profit_pct": 0.1,
        "stop_loss_pct": 0.3,
    },
}


def prompt_float(prompt: str, default: float) -> float:
    raw = input(f"{prompt} [{default}]: ")
    return float(raw) if raw.strip() else default


def prompt_profile() -> str:
    print("Perfiles disponibles: conservador, equilibrado, agresivo")
    raw = input("Selecciona perfil [equilibrado]: ")
    profile = raw.strip().lower() or "equilibrado"
    return profile if profile in PROFILES else "equilibrado"


def main() -> None:
    set_random_seed(42)
    data_path = Path(input("Ruta al CSV de datos [data/historico_1min_clean.csv]: ") or "data/historico_1min_clean.csv")
    quality = load_price_data(data_path)
    data = quality.data

    profile = prompt_profile()
    overrides = PROFILES[profile]

    initial_btc = prompt_float("BTC inicial", 0.1)
    fee_pct = prompt_float("Fee pct", 0.001)
    slippage_pct = prompt_float("Slippage pct", 0.0005)

    median_price = float(data["close"].median())
    max_price = float(data["close"].max())

    config = BacktestConfig(
        min_price=0.9 * median_price,
        max_price=1.1 * max_price,
        num_levels=int(overrides["num_levels"]),
        allocation_per_buy_usd=float(overrides["allocation_per_buy_usd"]),
        fee_pct=fee_pct,
        slippage_pct=slippage_pct,
        initial_btc=initial_btc,
        take_profit_pct=float(overrides["take_profit_pct"]),
        stop_loss_pct=float(overrides["stop_loss_pct"]),
    )

    backtester = GridBacktester(data, config, run_prefix=f"cli_{profile}")
    result = backtester.run({
        "missing_pct": quality.quality.missing_pct,
        "zero_volume_pct": quality.quality.zero_volume_pct,
        "adjustments": quality.quality.adjustments,
    })

    print(json.dumps({
        "final_btc": result.final_btc,
        "final_usd": result.final_usd,
        "pct_return_btc": result.pct_return_btc,
        "n_trades": result.n_trades,
    }, indent=2))


if __name__ == "__main__":
    main()
