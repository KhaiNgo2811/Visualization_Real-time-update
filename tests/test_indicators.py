import numpy as np
import pandas as pd

from core.indicators import INDICATOR_COLS, add_indicators


def make_df(n=120, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) * 1.001,
                         "low": np.minimum(open_, close) * 0.999, "close": close, "volume": rng.uniform(1, 10, n)})


def test_adds_all_indicator_columns():
    d = add_indicators(make_df())
    assert all(c in d.columns for c in INDICATOR_COLS)


def test_sma_matches_manual_mean():
    df = make_df()
    d = add_indicators(df)
    assert np.isclose(d["sma20"].iloc[-1], df["close"].tail(20).mean())
    assert np.isclose(d["sma50"].iloc[-1], df["close"].tail(50).mean())


def test_rsi_in_range_and_bollinger_order():
    d = add_indicators(make_df()).dropna()
    assert d["rsi14"].between(0, 100).all()
    assert (d["bb_up"] >= d["bb_mid"]).all() and (d["bb_mid"] >= d["bb_low"]).all()


def test_rsi_high_when_always_rising():
    close = np.linspace(100, 200, 60)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert add_indicators(df)["rsi14"].iloc[-1] > 99
