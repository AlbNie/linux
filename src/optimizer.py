from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import optuna
import pandas as pd

from .backtester import BacktestConfig, GridBacktester
from .data_loader import DataQualityReport, load_price_data
from .utils import create_run_dir, dump_json, set_random_seed

logger = logging.getLogger(__name__)


def temporal_folds(df: pd.DataFrame, n_folds: int = 3) -> List[pd.DataFrame]:
    fold_size = len(df) // n_folds
    folds = []
    for i in range(n_folds):
        start = i * fold_size
        end = (i + 1) * fold_size if i < n_folds - 1 else len(df)
        folds.append(df.iloc[start:end])
    return folds


def objective_factory(price_path: Path, base_params: Dict[str, float], data_quality: DataQualityReport, max_allowed_drawdown: float, max_trades_per_day: int):
    price_data = load_price_data(price_path).data
    folds = temporal_folds(price_data, n_folds=3)

    def objective(trial: optuna.Trial) -> float:
        params = base_params.copy()
        median_price = float(price_data["close"].median())
        max_price_hist = float(price_data["close"].max())

        params.update(
            {
                "min_price": trial.suggest_float("min_price", 0.5 * median_price, 0.95 * median_price),
                "max_price": trial.suggest_float("max_price", 1.05 * median_price, 1.5 * max_price_hist),
                "num_levels": trial.suggest_int("num_levels", 5, 60),
                "allocation_per_buy_usd": trial.suggest_float("allocation_per_buy_usd", 5.0, 5000.0),
                "fee_pct": trial.suggest_float("fee_pct", 0.00005, 0.005),
                "slippage_pct": trial.suggest_float("slippage_pct", 0.0, 0.01),
                "take_profit_pct": trial.suggest_float("take_profit_pct", 0.0, 0.2),
                "stop_loss_pct": trial.suggest_float("stop_loss_pct", 0.0, 0.5),
                "initial_btc": trial.suggest_float("initial_btc", 0.01, 0.5),
            }
        )
        penalties = 0.0
        final_btc_scores = []
        for fold_idx, fold_data in enumerate(folds):
            if fold_data.empty:
                continue
            config = BacktestConfig(
                min_price=params["min_price"],
                max_price=params["max_price"],
                num_levels=int(params["num_levels"]),
                allocation_per_buy_usd=float(params["allocation_per_buy_usd"]),
                fee_pct=float(params["fee_pct"]),
                slippage_pct=float(params["slippage_pct"]),
                take_profit_pct=float(params["take_profit_pct"]),
                stop_loss_pct=float(params["stop_loss_pct"]),
                initial_btc=float(params["initial_btc"]),
                min_trade_btc=base_params.get("min_trade_btc", 1e-6),
                min_trade_usd=base_params.get("min_trade_usd", 1.0),
                exposure_limit_pct=base_params.get("exposure_limit_pct", 1.0),
                max_position_pct=base_params.get("max_position_pct", 1.0),
                forced_close=base_params.get("forced_close", True),
                max_allowed_drawdown=max_allowed_drawdown,
                max_trades_per_day=max_trades_per_day,
            )
            bt = GridBacktester(fold_data, config, run_prefix=f"optuna_fold{fold_idx}")
            result = bt.run(data_quality.__dict__)
            final_btc_scores.append(result.final_btc)
            if result.max_drawdown < -max_allowed_drawdown:
                penalties += abs(result.max_drawdown)
            if result.trade_limit_violations > 0:
                penalties += 0.1 * result.trade_limit_violations
        avg_final_btc = float(np.mean(final_btc_scores)) if final_btc_scores else 0.0
        return -(avg_final_btc - penalties)

    return objective


def run_optimization(price_path: Path, n_trials: int = 10, study_name: str = "grid", storage: str = "sqlite:///results/optuna.db", n_jobs: int = 1) -> optuna.Study:
    set_random_seed(42)
    quality = load_price_data(price_path)
    base_params = {
        "min_trade_btc": 1e-5,
        "min_trade_usd": 10.0,
        "exposure_limit_pct": 0.8,
        "max_position_pct": 0.9,
        "forced_close": True,
    }
    objective = objective_factory(price_path, base_params, quality.quality, max_allowed_drawdown=0.35, max_trades_per_day=200)
    sampler = optuna.samplers.TPESampler(seed=42)
    pruner = optuna.pruners.MedianPruner(n_warmup_steps=2)
    study = optuna.create_study(study_name=study_name, storage=storage, sampler=sampler, pruner=pruner, direction="minimize", load_if_exists=True)
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)

    top_trials = sorted(study.trials, key=lambda t: t.value)[:50]
    records = [
        {
            "trial_id": t.number,
            "value": t.value,
            **t.params,
        }
        for t in top_trials
        if t.state == optuna.trial.TrialState.COMPLETE
    ]
    artifacts = create_run_dir("optuna")
    dump_json(artifacts.summary_path, {"best_trial": study.best_trial.params, "best_value": study.best_value})
    dump_json(artifacts.metrics_path, {"top_trials": records})
    return study


__all__ = ["run_optimization"]
