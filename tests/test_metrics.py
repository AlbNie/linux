import pytest

pandas = pytest.importorskip("pandas")
pd = pandas

from src.metrics import max_drawdown


def test_max_drawdown():
    series = pd.Series([1.0, 1.1, 0.9, 1.2, 1.0])
    dd = max_drawdown(series)
    assert dd == pytest.approx(-0.181818, rel=1e-3)
