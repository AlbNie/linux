#!/usr/bin/env bash
set -euo pipefail

DATA=${1:-data/historico_1min_clean.csv}
TRIALS=${2:-5}

python grid_optimizer.py --data "$DATA" --trials "$TRIALS" --update-prices
python grid_backtest.py --data "$DATA" --update-prices

mkdir -p results
python - <<'PY'
import json
from pathlib import Path

summary = []
optuna_path = Path('results/optuna_best.json')
if optuna_path.exists():
    payload = json.loads(optuna_path.read_text())
    summary.append({'label': 'optuna_best', 'final_btc': -payload['best_value'], **payload['best_params']})

backtest_path = Path('results/backtest.json')
if backtest_path.exists():
    payload = json.loads(backtest_path.read_text())
    summary.append({'label': 'latest_backtest', 'final_btc': payload['final_btc'], 'pct_return_btc': payload['pct_return_btc']})

out_path = Path('results/summary.csv')
if summary:
    headers = sorted(summary[0].keys())
    with out_path.open('w') as fh:
        fh.write(','.join(headers) + '\n')
        for row in summary:
            fh.write(','.join(str(row.get(h, '')) for h in headers) + '\n')
PY
