"""Tải dữ liệu nến (OHLCV) từ API công khai của sàn giao dịch.

Thứ tự ưu tiên:
    1. Binance Market Data API (data-api.binance.vision, không cần API key)
    2. Kraken Public API (dự phòng khi Binance bị chặn theo khu vực)
    3. Dữ liệu MÔ PHỎNG (chỉ dùng khi cả hai sàn đều lỗi; luôn được gắn nhãn rõ ràng)
"""
from __future__ import annotations

import time
import zlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests

# Mã giao dịch của từng đồng trên 2 sàn: (Binance, Kraken)
SYMBOLS: dict[str, tuple[str, str]] = {
    "BTC": ("BTCUSDT", "XBTUSD"),
    "ETH": ("ETHUSDT", "ETHUSD"),
    "SOL": ("SOLUSDT", "SOLUSD"),
    "XRP": ("XRPUSDT", "XRPUSD"),
    "DOGE": ("DOGEUSDT", "DOGEUSD"),
}
INTERVAL_MIN: dict[str, int] = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
KRAKEN_URL = "https://api.kraken.com/0/public/OHLC"
HEADERS = {"User-Agent": "Mozilla/5.0 (candlestick-realtime-app)"}
TIMEOUT = 15

NUMERIC_COLS = ["open", "high", "low", "close", "volume", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote"]
COLUMNS = ["time", "open", "high", "low", "close", "volume", "quote_volume", "trades",
           "taker_buy_base", "taker_buy_quote", "close_time", "open_time"]

SYNTHETIC_BASE = {"BTC": 85000.0, "ETH": 3200.0, "SOL": 150.0, "XRP": 2.4, "DOGE": 0.18}


@dataclass
class FetchResult:
    df: pd.DataFrame
    source: str                       # "Binance" | "Kraken" | "Mô phỏng"
    errors: list[str] = field(default_factory=list)

    @property
    def is_synthetic(self) -> bool:
        return self.source == "Mô phỏng"


def _finalize(d: pd.DataFrame) -> pd.DataFrame:
    """Ép kiểu số, chuẩn hóa cột thời gian (UTC, không múi giờ), bỏ trùng và sắp xếp."""
    d = d.copy()
    d[NUMERIC_COLS] = d[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    d = d.dropna(subset=["open", "high", "low", "close"])
    d = d.drop_duplicates("open_time").sort_values("open_time")
    return d[COLUMNS].reset_index(drop=True)


def fetch_binance(symbol: str, interval: str, limit: int, session=requests) -> pd.DataFrame:
    r = session.get(BINANCE_URL, headers=HEADERS, timeout=TIMEOUT,
                    params={"symbol": symbol, "interval": interval, "limit": min(limit, 1000)})
    r.raise_for_status()
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
            "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
    d = pd.DataFrame(r.json(), columns=cols)
    d["time"] = pd.to_datetime(d["open_time"], unit="ms")
    return _finalize(d)


def fetch_kraken(pair: str, interval: str, limit: int, session=requests) -> pd.DataFrame:
    r = session.get(KRAKEN_URL, headers=HEADERS, timeout=TIMEOUT,
                    params={"pair": pair, "interval": INTERVAL_MIN[interval]})
    r.raise_for_status()
    js = r.json()
    if js.get("error"):
        raise RuntimeError(js["error"])
    rows = [v for k, v in js["result"].items() if k != "last"][0][-limit:]
    d = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "vwap", "volume", "trades"])
    d["time"] = pd.to_datetime(d["open_time"], unit="s")
    d["quote_volume"] = pd.to_numeric(d["vwap"]) * pd.to_numeric(d["volume"])     # xấp xỉ giá trị giao dịch
    d["open_time"] = d["open_time"] * 1000                                          # đồng bộ đơn vị ms với Binance
    for c in ("close_time", "taker_buy_base", "taker_buy_quote"):                  # cột Kraken không có
        d[c] = np.nan
    return _finalize(d)


def synthetic_klines(coin: str, interval: str, limit: int) -> pd.DataFrame:
    """Dữ liệu MÔ PHỎNG (random walk) - chỉ để giao diện vẫn chạy khi mất kết nối."""
    step = INTERVAL_MIN[interval] * 60
    now = time.time()
    end = int(now // step * step)
    ts = end - step * (limit - 1) + step * np.arange(limit)
    rng = np.random.default_rng(zlib.crc32(f"{coin}{interval}{end // step}".encode()))
    vol = 0.0006 * np.sqrt(INTERVAL_MIN[interval])
    close = SYNTHETIC_BASE.get(coin, 100.0) * np.exp(np.cumsum(rng.normal(0, vol, limit)))
    close[-1] *= 1 + 0.0004 * np.sin(now / 3.0)                # nến cuối "nhấp nháy" theo thời gian
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, limit)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, limit)))
    volume = rng.uniform(1, 40, limit)
    d = pd.DataFrame({"open_time": ts * 1000, "open": open_, "high": high, "low": low, "close": close,
                      "volume": volume, "quote_volume": volume * close, "trades": rng.integers(50, 900, limit),
                      "taker_buy_base": volume * 0.5, "taker_buy_quote": volume * close * 0.5,
                      "close_time": ts * 1000 + step * 1000 - 1})
    d["time"] = pd.to_datetime(d["open_time"], unit="ms")
    return _finalize(d)


def get_klines(coin: str = "BTC", interval: str = "1m", limit: int = 300, *,
               allow_synthetic: bool = True, session=requests) -> FetchResult:
    """Tải `limit` nến gần nhất, tự chuyển nguồn khi lỗi. Cột `time` là giờ UTC (không kèm múi giờ)."""
    errors: list[str] = []
    binance_sym, kraken_sym = SYMBOLS[coin]
    for name, fn, sym in (("Binance", fetch_binance, binance_sym), ("Kraken", fetch_kraken, kraken_sym)):
        try:
            d = fn(sym, interval, limit, session=session)
            if len(d):
                return FetchResult(d, name, errors)
            errors.append(f"{name}: dữ liệu rỗng")
        except Exception as e:                                   # noqa: BLE001 - cần bắt mọi lỗi mạng/định dạng
            errors.append(f"{name}: {e}")
    if allow_synthetic:
        return FetchResult(synthetic_klines(coin, interval, limit), "Mô phỏng", errors)
    raise RuntimeError("Không tải được dữ liệu từ cả 2 sàn: " + " | ".join(errors))
