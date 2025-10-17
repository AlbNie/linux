from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Order:
    timestamp: datetime
    side: str  # "buy" or "sell"
    order_type: str  # "market" or "limit"
    price: float
    size_btc: Optional[float] = None
    size_usd: Optional[float] = None
    tag: str = ""


@dataclass
class Trade:
    timestamp: datetime
    side: str
    price: float
    executed_btc: float
    executed_usd: float
    fee_paid_btc: float
    fee_paid_usd: float
    slippage_btc: float
    slippage_usd: float
    tag: str = ""


@dataclass
class Portfolio:
    cash_usd: float
    btc: float
    exposure_limit_pct: float
    max_position_pct: float
    min_trade_btc: float
    min_trade_usd: float

    trades: List[Trade] = field(default_factory=list)

    def available_exposure_btc(self, price: float) -> float:
        total_btc_equiv = self.total_btc(price)
        max_total = total_btc_equiv * self.exposure_limit_pct
        current_exposure = max(self.btc, 0.0)
        return max(max_total - current_exposure, 0.0)

    def total_btc(self, price: float) -> float:
        if price <= 0:
            raise ValueError("Price must be positive")
        return self.btc + self.cash_usd / price

    def record_trade(self, trade: Trade) -> None:
        self.trades.append(trade)


class OrderEngine:
    def __init__(
        self,
        portfolio: Portfolio,
        fee_pct: float,
        slippage_pct: float,
    ) -> None:
        self.portfolio = portfolio
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct

    def _check_min_trade(self, size_btc: float, size_usd: float) -> bool:
        if size_btc < self.portfolio.min_trade_btc and size_usd < self.portfolio.min_trade_usd:
            logger.debug(
                "Skipping micro trade size_btc=%.8f size_usd=%.2f", size_btc, size_usd
            )
            return False
        return True

    def _apply_fee(self, qty_btc: float, price: float) -> float:
        return qty_btc * self.fee_pct

    def execute(self, order: Order) -> Optional[Trade]:
        if order.order_type not in {"market", "limit"}:
            raise ValueError(f"Unsupported order type {order.order_type}")
        price = order.price
        slippage_factor = 1 + self.slippage_pct if order.side == "buy" else 1 - self.slippage_pct
        effective_price = price * slippage_factor

        size_btc = order.size_btc if order.size_btc is not None else (order.size_usd or 0.0) / effective_price
        size_usd = order.size_usd if order.size_usd is not None else size_btc * effective_price

        if size_btc <= 0 or size_usd <= 0:
            return None

        if not self._check_min_trade(size_btc, size_usd):
            return None

        fee_btc = self._apply_fee(size_btc, price)
        fee_usd = fee_btc * effective_price

        if order.side == "buy":
            total_cost_usd = size_usd + fee_usd
            if total_cost_usd > self.portfolio.cash_usd + 1e-9:
                logger.debug("Insufficient USD to execute buy order")
                return None
            if size_btc + self.portfolio.btc > self.portfolio.total_btc(price) * self.portfolio.max_position_pct:
                logger.debug("Max position exceeded for buy order")
                return None
            if size_btc > self.portfolio.available_exposure_btc(price):
                logger.debug("Exposure limit reached")
                return None
            self.portfolio.cash_usd -= total_cost_usd
            self.portfolio.btc += size_btc
        else:
            total_btc_cost = size_btc + fee_btc
            if total_btc_cost > self.portfolio.btc + 1e-9:
                logger.debug("Insufficient BTC to execute sell order")
                return None
            self.portfolio.btc -= total_btc_cost
            self.portfolio.cash_usd += size_usd - fee_usd

        trade = Trade(
            timestamp=order.timestamp,
            side=order.side,
            price=effective_price,
            executed_btc=size_btc,
            executed_usd=size_usd,
            fee_paid_btc=fee_btc,
            fee_paid_usd=fee_usd,
            slippage_btc=size_btc * (slippage_factor - 1),
            slippage_usd=size_usd * (slippage_factor - 1),
            tag=order.tag,
        )
        self.portfolio.record_trade(trade)
        return trade


__all__ = ["Order", "Trade", "Portfolio", "OrderEngine"]
