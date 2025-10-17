import pytest

pandas = pytest.importorskip("pandas")
pd = pandas

from src.backtester import BacktestConfig, GridBacktester


def test_forced_close_executes():
    timestamps = pd.date_range("2023-01-06 23:58", periods=3, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [20000, 20010, 20020],
            "high": [20010, 20020, 20030],
            "low": [19990, 20000, 20010],
            "close": [20005, 20015, 20025],
            "volume": [10, 10, 10],
        },
        index=timestamps,
    )
    config = BacktestConfig(
        min_price=19900,
        max_price=20500,
        num_levels=5,
        allocation_per_buy_usd=50,
        fee_pct=0.0,
        slippage_pct=0.0,
        initial_btc=0.1,
        take_profit_pct=0.0,
        stop_loss_pct=0.0,
    )
    bt = GridBacktester(df, config)
    result = bt.run({"missing_pct": 0.0, "zero_volume_pct": 0.0, "adjustments": 0})
    assert result.trade_limit_violations == 0
    assert result.n_trades >= 1
