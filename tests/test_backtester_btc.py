import pytest

pandas = pytest.importorskip("pandas")
pd = pandas

from src.backtester import BacktestConfig, GridBacktester


def test_final_btc_computation():
    timestamps = pd.date_range("2023-01-02", periods=5, freq="1min", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [20000, 19950, 19900, 19850, 19800],
            "high": [20010, 19960, 19910, 19860, 19810],
            "low": [19990, 19900, 19850, 19800, 19750],
            "close": [19950, 19900, 19850, 19800, 19750],
            "volume": [10, 10, 10, 10, 10],
        },
        index=timestamps,
    )
    config = BacktestConfig(
        min_price=19700,
        max_price=20000,
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
    assert result.final_btc >= config.initial_btc
