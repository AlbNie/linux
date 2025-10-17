from __future__ import annotations

import numpy as np
import pandas as pd


def compute_equity_curve(trades_df: pd.DataFrame, price_series: pd.Series, initial_btc: float, initial_usd: float) -> pd.DataFrame:
    btc = initial_btc
    usd = initial_usd
    equity_records = []
    trade_iter = trades_df.sort_values("timestamp").itertuples(index=False) if not trades_df.empty else []
    trade_iter = iter(trade_iter)
    next_trade = None
    try:
        next_trade = next(trade_iter)
    except StopIteration:
        next_trade = None

    for ts, price in price_series.iteritems():
        while next_trade is not None and next_trade.timestamp == ts:
            if next_trade.side == "buy":
                btc += next_trade.executed_btc
                usd -= next_trade.executed_usd + next_trade.fee_paid_usd
            else:
                btc -= next_trade.executed_btc + next_trade.fee_paid_btc
                usd += next_trade.executed_usd - next_trade.fee_paid_usd
            try:
                next_trade = next(trade_iter)
            except StopIteration:
                next_trade = None
        total_btc = btc + usd / price
        total_usd = usd + btc * price
        equity_records.append({
            "timestamp": ts,
            "portfolio_btc": total_btc,
            "portfolio_usd": total_usd,
            "btc": btc,
            "usd": usd,
        })
    return pd.DataFrame(equity_records).set_index("timestamp")


def max_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    return float(drawdown.min())


def volatility(returns: pd.Series) -> float:
    return float(returns.std(ddof=0))


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    vol = returns.std(ddof=0)
    if vol == 0:
        return 0.0
    excess = returns.mean() - risk_free_rate
    return float(excess / vol)


__all__ = ["compute_equity_curve", "max_drawdown", "volatility", "sharpe_ratio"]
