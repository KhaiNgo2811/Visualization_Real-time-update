"""Chỉ báo kỹ thuật: SMA, EMA, MACD, Bollinger, RSI, lợi suất..."""
from __future__ import annotations

import pandas as pd

INDICATOR_COLS = ["sma20", "sma50", "ema12", "ema26", "macd", "macd_signal", "macd_hist",
                  "bb_mid", "bb_up", "bb_low", "rsi14", "ret_pct", "typical", "vol_sma20"]


def add_indicators(d: pd.DataFrame) -> pd.DataFrame:
    """Thêm 14 cột chỉ báo vào DataFrame nến (cần cột open, high, low, close, volume)."""
    d = d.copy()
    c = d["close"]
    d["sma20"], d["sma50"] = c.rolling(20).mean(), c.rolling(50).mean()
    d["ema12"], d["ema26"] = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    d["macd"] = d["ema12"] - d["ema26"]
    d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["macd_hist"] = d["macd"] - d["macd_signal"]
    sd = c.rolling(20).std()
    d["bb_mid"], d["bb_up"], d["bb_low"] = d["sma20"], d["sma20"] + 2 * sd, d["sma20"] - 2 * sd
    delta = c.diff()                                              # RSI theo Wilder (14 kỳ)
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = 100 - 100 / (1 + gain / loss)
    rsi = rsi.where(loss != 0, 100.0)                             # không có phiên giảm nào -> RSI = 100
    d["rsi14"] = rsi.mask((loss == 0) & (gain == 0), 50.0)        # giá đi ngang hoàn toàn -> 50
    d["ret_pct"] = c.pct_change() * 100
    d["typical"] = (d["high"] + d["low"] + c) / 3
    d["vol_sma20"] = d["volume"].rolling(20).mean()
    return d
