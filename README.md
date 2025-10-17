# BTC Accumulation Grid Backtester

This project provides a reproducible research environment for testing a BTC accumulation grid strategy with Optuna optimization.

## Features

- Vectorised grid execution engine with market and limit orders.
- Fees, slippage, exposure and minimum trade size controls.
- Weekly forced-close on Fridays at 23:59.
- Optuna optimisation with median pruning and reproducible seeds.
- JSON summaries, CSV trades, and PNG equity curves per run.
- Temporal walk-forward validation and stress testing hooks.

## Project Structure

```
data/                # Sample OHLCV data
results/             # Backtest and optimisation outputs
src/                 # Backtester, order engine, optimiser
notebooks/           # Exploratory notebooks
tests/               # Pytest suite
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The project relies on `pandas`, `numpy`, `optuna`, and `matplotlib`.

## Usage

### Single Backtest

```bash
python grid_backtest.py --data data/historico_1min_clean.csv
```

Outputs:

- `results/backtest.json` – metrics including `final_btc` and `pct_return_btc`.
- `results/events.csv` – trade log.
- A dated folder under `results/` containing raw artifacts.

### Optimisation

```bash
python grid_optimizer.py --data data/historico_1min_clean.csv --trials 20
```

This command stores the Optuna study in `results/optuna.db` and exports `results/optuna_best.json`.

### Run Everything

```bash
bash run_all.sh data/historico_1min_clean.csv 10
```

The script runs optimisation and a backtest, aggregating results into `results/summary.csv`.

### Interactive CLI

```bash
python cli.py
```

Follow the prompts to select conservative, balanced, or aggressive presets.

## Reproducibility

- Random seeds fixed to 42.
- Optuna study stored in SQLite (`results/optuna.db`).
- Each run creates a dated directory under `results/` with JSON and CSV artifacts.

## Testing

Run the unit tests with:

```bash
pytest
```

The suite covers drawdown calculation, portfolio conversions, forced weekly closure, and negative balance prevention.

## Backtests and Walk-Forward

To replicate different horizons, slice your CSV before running `grid_backtest.py` or configure dedicated datasets. The optimiser performs a 3-fold temporal walk-forward across the supplied dataset. Stress tests can be simulated by increasing `--slippage-pct` and `--fee-pct` or by modifying the configuration passed to `GridBacktester`.

## USD to BTC Conversion

All reporting is in BTC via `final_btc` and `pct_return_btc`. USD values are tracked for transparency and converted at the latest close price.
