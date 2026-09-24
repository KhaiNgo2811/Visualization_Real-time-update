import pandas as pd
import pytest

from core.charts import candle_fig
from core.indicators import add_indicators
from core.data import synthetic_klines


@pytest.fixture()
def frame():
    d = add_indicators(synthetic_klines("BTC", "1m", 200)).tail(120).reset_index(drop=True)
    d["time_local"] = d["time"]
    return d


@pytest.mark.parametrize("panel,rows", [("RSI", 3), ("MACD", 3), ("Không", 2)])
def test_panels(frame, panel, rows):
    fig = candle_fig(frame, "test", panel=panel)
    assert any(t.type == "candlestick" for t in fig.data)
    assert len({getattr(t, "yaxis", "y") for t in fig.data}) == rows


def test_toggle_overlays(frame):
    full = candle_fig(frame, "t", show_sma=True, show_bb=True)
    bare = candle_fig(frame, "t", show_sma=False, show_bb=False)
    assert len(full.data) > len(bare.data)
