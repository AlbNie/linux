from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .metrics import max_drawdown, sharpe_ratio, volatility
from .orders import Order, OrderEngine, Portfolio
from .utils import RunArtifacts, create_run_dir, dump_json

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    min_price: float
    max_price: float
    num_levels: int
    allocation_per_buy_usd: float
    fee_pct: float
    slippage_pct: float
    initial_btc: float = 0.1
    initial_usd: Optional[float] = None
    min_trade_btc: float = 1e-6
    min_trade_usd: float = 1.0
    exposure_limit_pct: float = 1.0
    max_position_pct: float = 1.0
    take_profit_pct: float = 0.0
    stop_loss_pct: float = 0.0
    block_size: int = 1440
    forced_close: bool = True
    max_allowed_drawdown: float = 0.35
    max_trades_per_day: int = 200
    close_on: time = time(23, 59)


@dataclass
class BacktestResult:
    final_btc: float
    final_usd: float
    pct_return_btc: float
    n_trades: int
    max_drawdown: float
    volatility_est: float
    sharpe_approx: float
    trade_limit_violations: int
    equity_curve_path: Path
    trades_path: Path
    metrics_path: Path
    params_path: Path
    summary_path: Path
    figure_path: Path
    data_quality: Dict[str, float]


class GridBacktester:
    def __init__(self, price_data: pd.DataFrame, config: BacktestConfig, run_prefix: str = "backtest") -> None:
        self.price_data = price_data
        self.config = config
        self.run_prefix = run_prefix
        self.artifacts: Optional[RunArtifacts] = None

    def _init_portfolio(self) -> Portfolio:
        initial_price = float(self.price_data["close"].iloc[0])
        initial_usd = self.config.initial_usd
        if initial_usd is None:
            initial_usd = self.config.initial_btc * initial_price
        portfolio = Portfolio(
            cash_usd=float(initial_usd),
            btc=float(self.config.initial_btc),
            exposure_limit_pct=self.config.exposure_limit_pct,
            max_position_pct=self.config.max_position_pct,
            min_trade_btc=self.config.min_trade_btc,
            min_trade_usd=self.config.min_trade_usd,
        )
        return portfolio

    def _forced_close_required(self, timestamp: pd.Timestamp) -> bool:
        if not self.config.forced_close:
            return False
        if timestamp.weekday() != 4:
            return False
        return timestamp.time() >= self.config.close_on

    def run(self, data_quality: Dict[str, float]) -> BacktestResult:
        if self.price_data.empty:
            raise ValueError("Price data is empty")
        self.artifacts = create_run_dir(self.run_prefix)
        portfolio = self._init_portfolio()
        engine = OrderEngine(portfolio, fee_pct=self.config.fee_pct, slippage_pct=self.config.slippage_pct)

        level_prices = np.linspace(self.config.min_price, self.config.max_price, self.config.num_levels)
        level_state = np.zeros(self.config.num_levels, dtype=bool)
        level_position_btc = np.zeros(self.config.num_levels)
        entry_prices = np.zeros(self.config.num_levels)

        trade_counts: Dict[str, int] = {}
        trade_limit_violations = 0
        equity_records: List[Dict[str, float]] = []

        for start in range(0, len(self.price_data), self.config.block_size):
            block = self.price_data.iloc[start : start + self.config.block_size]
            lows = block["low"].values
            highs = block["high"].values
            closes = block["close"].values
            timestamps = block.index

            for idx, ts in enumerate(timestamps):
                close_price = float(closes[idx])
                low_price = float(lows[idx])
                high_price = float(highs[idx])

                day_key = ts.strftime("%Y-%m-%d")
                trade_counts.setdefault(day_key, 0)

                triggered_buy = low_price <= level_prices
                new_buys_mask = triggered_buy & (~level_state)
                if np.any(new_buys_mask):
                    for level_idx in np.where(new_buys_mask)[0]:
                        size_usd = self.config.allocation_per_buy_usd
                        order = Order(
                            timestamp=ts.to_pydatetime(),
                            side="buy",
                            order_type="limit",
                            price=float(level_prices[level_idx]),
                            size_usd=size_usd,
                            tag=f"level_{level_idx}",
                        )
                        trade = engine.execute(order)
                        if trade:
                            level_state[level_idx] = True
                            level_position_btc[level_idx] = trade.executed_btc
                            entry_prices[level_idx] = trade.price
                            trade_counts[day_key] += 1

                if self.config.take_profit_pct > 0:
                    tp_prices = entry_prices * (1 + self.config.take_profit_pct)
                    tp_mask = level_state & (high_price >= tp_prices)
                    if np.any(tp_mask):
                        for level_idx in np.where(tp_mask)[0]:
                            position_btc = level_position_btc[level_idx]
                            if position_btc <= 0:
                                continue
                            order = Order(
                                timestamp=ts.to_pydatetime(),
                                side="sell",
                                order_type="limit",
                                price=float(tp_prices[level_idx]),
                                size_btc=float(position_btc),
                                tag=f"tp_{level_idx}",
                            )
                            trade = engine.execute(order)
                            if trade:
                                level_state[level_idx] = False
                                level_position_btc[level_idx] = 0.0
                                entry_prices[level_idx] = 0.0
                                trade_counts[day_key] += 1

                if self.config.stop_loss_pct > 0:
                    sl_prices = entry_prices * (1 - self.config.stop_loss_pct)
                    sl_mask = level_state & (low_price <= sl_prices)
                    if np.any(sl_mask):
                        for level_idx in np.where(sl_mask)[0]:
                            position_btc = level_position_btc[level_idx]
                            if position_btc <= 0:
                                continue
                            order = Order(
                                timestamp=ts.to_pydatetime(),
                                side="sell",
                                order_type="market",
                                price=close_price,
                                size_btc=float(position_btc),
                                tag=f"sl_{level_idx}",
                            )
                            trade = engine.execute(order)
                            if trade:
                                level_state[level_idx] = False
                                level_position_btc[level_idx] = 0.0
                                entry_prices[level_idx] = 0.0
                                trade_counts[day_key] += 1

                if self._forced_close_required(ts):
                    position_btc = portfolio.btc
                    if position_btc > 0:
                        order = Order(
                            timestamp=ts.to_pydatetime(),
                            side="sell",
                            order_type="market",
                            price=close_price,
                            size_btc=float(position_btc),
                            tag="forced_close",
                        )
                        trade = engine.execute(order)
                        if trade:
                            level_state[:] = False
                            level_position_btc[:] = 0.0
                            entry_prices[:] = 0.0
                            trade_counts[day_key] += 1

                if trade_counts[day_key] > self.config.max_trades_per_day:
                    logger.warning("Trade limit exceeded for %s, skipping remaining signals", day_key)
                    trade_limit_violations += 1
                    continue

                total_btc = portfolio.total_btc(close_price)
                total_usd = portfolio.cash_usd + portfolio.btc * close_price
                equity_records.append(
                    {
                        "timestamp": ts,
                        "portfolio_btc": total_btc,
                        "portfolio_usd": total_usd,
                        "btc": portfolio.btc,
                        "usd": portfolio.cash_usd,
                    }
                )

        trades_df = pd.DataFrame([t.__dict__ for t in portfolio.trades])
        equity_curve = pd.DataFrame(equity_records).set_index("timestamp")

        returns = equity_curve["portfolio_btc"].pct_change().fillna(0.0)
        drawdown = max_drawdown(equity_curve["portfolio_btc"])
        vol_est = volatility(returns)
        sharpe = sharpe_ratio(returns)

        final_btc = float(equity_curve["portfolio_btc"].iloc[-1]) if not equity_curve.empty else portfolio.total_btc(self.price_data["close"].iloc[-1])
        final_usd = float(equity_curve["portfolio_usd"].iloc[-1]) if not equity_curve.empty else portfolio.cash_usd + portfolio.btc * self.price_data["close"].iloc[-1]
        if drawdown < -self.config.max_allowed_drawdown:
            penalty = abs(drawdown) * 0.1
            final_btc -= penalty

        pct_return_btc = final_btc / self.config.initial_btc - 1

        metrics = {
            "final_btc": final_btc,
            "final_usd": final_usd,
            "pct_return_btc": pct_return_btc,
            "n_trades": len(trades_df),
            "max_drawdown": drawdown,
            "volatility_est": vol_est,
            "sharpe_approx": sharpe,
            "trade_limit_violations": trade_limit_violations,
        }
        metrics.update(data_quality)

        import matplotlib.pyplot as plt

        equity_curve.to_csv(self.artifacts.equity_path)
        trades_df.to_csv(self.artifacts.trades_path, index=False)
        dump_json(self.artifacts.params_path, asdict(self.config))
        dump_json(self.artifacts.metrics_path, metrics)
        summary_payload = {
            "metrics": metrics,
            "paths": {
                "equity_curve": str(self.artifacts.equity_path),
                "trades": str(self.artifacts.trades_path),
                "figure": str(self.artifacts.figure_path),
            },
        }
        dump_json(self.artifacts.summary_path, summary_payload)

        if not equity_curve.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            equity_curve["portfolio_btc"].plot(ax=ax, label="Portfolio BTC")
            equity_curve["portfolio_usd"].plot(ax=ax, label="Portfolio USD")
            ax.set_title("Portfolio Evolution")
            ax.legend()
            fig.tight_layout()
            fig.savefig(self.artifacts.figure_path)
            plt.close(fig)

        return BacktestResult(
            final_btc=final_btc,
            final_usd=final_usd,
            pct_return_btc=pct_return_btc,
            n_trades=len(trades_df),
            max_drawdown=drawdown,
            volatility_est=vol_est,
            sharpe_approx=sharpe,
            trade_limit_violations=trade_limit_violations,
            equity_curve_path=self.artifacts.equity_path,
            trades_path=self.artifacts.trades_path,
            metrics_path=self.artifacts.metrics_path,
            params_path=self.artifacts.params_path,
            summary_path=self.artifacts.summary_path,
            figure_path=self.artifacts.figure_path,
            data_quality=data_quality,
        )


__all__ = ["BacktestConfig", "BacktestResult", "GridBacktester"]
