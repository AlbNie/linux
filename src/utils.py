from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np


RUNS_DIR = Path("results")
LOG_DIR = Path("logs")


def configure_logging(run_dir: Path) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = run_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )


def set_random_seed(seed: int = 42) -> None:
    np.random.seed(seed)


@dataclass
class RunArtifacts:
    run_dir: Path
    params_path: Path
    metrics_path: Path
    trades_path: Path
    equity_path: Path
    summary_path: Path
    figure_path: Path


def create_run_dir(prefix: str) -> RunArtifacts:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{timestamp}_{np.random.randint(0, 1_000_000):06d}" / prefix
    run_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(run_dir)
    return RunArtifacts(
        run_dir=run_dir,
        params_path=run_dir / "params.json",
        metrics_path=run_dir / "metrics.json",
        trades_path=run_dir / "events.csv",
        equity_path=run_dir / "equity_curve.csv",
        summary_path=run_dir / "summary.json",
        figure_path=run_dir / "equity_curve.png",
    )


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


__all__ = [
    "RunArtifacts",
    "configure_logging",
    "create_run_dir",
    "dump_json",
    "ensure_parent",
    "load_json",
    "set_random_seed",
]
