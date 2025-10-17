from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    missing_pct: float
    zero_volume_pct: float
    adjustments: int


@dataclass
class PriceData:
    data: pd.DataFrame
    quality: DataQualityReport


EXPECTED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def _validate_columns(df: pd.DataFrame) -> None:
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")


def _repair_dataframe(df: pd.DataFrame, freq: Optional[str]) -> Tuple[pd.DataFrame, DataQualityReport]:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df.set_index("timestamp", inplace=True)

    missing_pct = float(df.isna().sum().sum()) / (df.shape[0] * df.shape[1]) if not df.empty else 0.0
    df.interpolate(method="time", inplace=True, limit_direction="both")
    df.fillna(method="bfill", inplace=True)

    zero_volume = (df["volume"] <= 0).mean() if not df.empty else 0.0
    adjustments = 0

    if freq:
        full_index = pd.date_range(df.index.min(), df.index.max(), freq=freq)
        if len(full_index) > len(df.index):
            df = df.reindex(full_index)
            adjustments += df.isna().sum().sum()
            df.interpolate(method="time", inplace=True, limit_direction="both")
            df.fillna(method="bfill", inplace=True)

    return df, DataQualityReport(missing_pct=missing_pct, zero_volume_pct=float(zero_volume), adjustments=int(adjustments))


def load_price_data(path: Path, freq: Optional[str] = "1min") -> PriceData:
    logger.info("Loading price data from %s", path)
    df = pd.read_csv(path)
    _validate_columns(df)
    repaired, report = _repair_dataframe(df, freq)
    logger.info(
        "Data quality -> missing_pct=%.4f zero_volume_pct=%.4f adjustments=%d",
        report.missing_pct,
        report.zero_volume_pct,
        report.adjustments,
    )
    return PriceData(data=repaired, quality=report)


def download_prices_if_needed(path: Path, symbol: str = "bitcoin", vs_currency: str = "usd", days: int = 90) -> None:
    """Optional helper using CoinGecko if the file is missing."""
    if path.exists():
        return
    try:
        import requests
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("requests is required to download prices") from exc

    logger.info("Downloading price data from CoinGecko for %s", symbol)
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": "minute"}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    prices = response.json()["prices"]
    volumes = response.json().get("total_volumes", [])

    records = []
    for idx, (ts, price) in enumerate(prices):
        volume = volumes[idx][1] if idx < len(volumes) else np.nan
        records.append({
            "timestamp": pd.to_datetime(ts, unit="ms"),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
        })
    df = pd.DataFrame(records)
    df.to_csv(path, index=False)


__all__ = ["PriceData", "load_price_data", "download_prices_if_needed", "DataQualityReport"]
