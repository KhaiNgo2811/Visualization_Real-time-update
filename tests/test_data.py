import pandas as pd
import pytest

from core import data


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    def raise_for_status(self):
        if self.status != 200:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self._p


BINANCE_ROWS = [[1_700_000_000_000 + i * 60_000, "100", "101", "99", "100.5", "2.5", 0, "250", 10, "1", "100", "0"]
                for i in range(5)]
KRAKEN_PAYLOAD = {"error": [], "result": {"XXBTZUSD": [[1_700_000_000 + i * 60, "100", "101", "99", "100.5", "100.2", "2.5", 10]
                                                       for i in range(5)], "last": 1}}


class Session:
    """Giả lập requests: có thể làm hỏng Binance hoặc Kraken."""
    def __init__(self, binance_ok=True, kraken_ok=True):
        self.binance_ok, self.kraken_ok = binance_ok, kraken_ok

    def get(self, url, **kw):
        if "binance" in url:
            return FakeResp(BINANCE_ROWS) if self.binance_ok else FakeResp([], 451)
        return FakeResp(KRAKEN_PAYLOAD) if self.kraken_ok else FakeResp({"error": ["EGeneral:Internal error"]})


def check_schema(d):
    assert list(d.columns) == data.COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(d["time"])
    assert d["time"].is_monotonic_increasing
    assert (d["high"] >= d[["open", "close"]].max(axis=1)).all()


def test_binance_parsing():
    r = data.get_klines("BTC", "1m", 5, session=Session())
    assert r.source == "Binance" and len(r.df) == 5
    check_schema(r.df)


def test_fallback_to_kraken():
    r = data.get_klines("BTC", "1m", 5, session=Session(binance_ok=False))
    assert r.source == "Kraken" and len(r.df) == 5
    assert any("Binance" in e for e in r.errors)
    check_schema(r.df)


def test_fallback_to_synthetic_is_labelled():
    r = data.get_klines("ETH", "5m", 100, session=Session(False, False))
    assert r.is_synthetic and r.source == "Mô phỏng" and len(r.df) == 100
    check_schema(r.df)


def test_raises_when_synthetic_disallowed():
    with pytest.raises(RuntimeError):
        data.get_klines("BTC", "1m", 5, allow_synthetic=False, session=Session(False, False))


@pytest.mark.parametrize("coin", list(data.SYMBOLS))
@pytest.mark.parametrize("interval", list(data.INTERVAL_MIN))
def test_synthetic_valid_for_all_pairs(coin, interval):
    check_schema(data.synthetic_klines(coin, interval, 80))
