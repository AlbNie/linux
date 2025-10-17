import datetime as dt

import pytest

numpy = pytest.importorskip("numpy")

from src.orders import Order, OrderEngine, Portfolio


def make_engine():
    portfolio = Portfolio(
        cash_usd=1000.0,
        btc=0.1,
        exposure_limit_pct=1.0,
        max_position_pct=1.0,
        min_trade_btc=1e-6,
        min_trade_usd=1.0,
    )
    engine = OrderEngine(portfolio, fee_pct=0.001, slippage_pct=0.0)
    return engine


def test_prevent_negative_balance():
    engine = make_engine()
    order = Order(timestamp=dt.datetime.utcnow(), side="buy", order_type="market", price=20000, size_usd=100000.0)
    trade = engine.execute(order)
    assert trade is None
    assert engine.portfolio.cash_usd == pytest.approx(1000.0)


def test_final_btc_conversion():
    engine = make_engine()
    order = Order(timestamp=dt.datetime.utcnow(), side="buy", order_type="market", price=20000, size_usd=200.0)
    trade = engine.execute(order)
    assert trade is not None
    final_btc = engine.portfolio.total_btc(20000)
    expected = engine.portfolio.btc + engine.portfolio.cash_usd / 20000
    assert final_btc == pytest.approx(expected)
