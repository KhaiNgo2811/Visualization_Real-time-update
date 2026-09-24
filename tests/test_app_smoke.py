"""Chạy thử toàn bộ app bằng Streamlit AppTest (không cần mở trình duyệt, không cần mạng)."""
import requests
from streamlit.testing.v1 import AppTest

from pathlib import Path

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _offline(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("offline (test)")
    monkeypatch.setattr(requests, "get", boom)


def test_app_renders_offline_with_synthetic_banner(monkeypatch):
    _offline(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("MÔ PHỎNG" in w.value for w in at.warning)
    assert len(at.metric) == 6


def test_app_switch_to_replay(monkeypatch):
    _offline(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.radio[0].set_value("Replay").run()
    assert not at.exception


def test_app_macd_panel_and_pause(monkeypatch):
    _offline(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=60).run()
    panel = [s for s in at.selectbox if s.label == "Chỉ báo tầng dưới"][0]
    panel.set_value("MACD").run()
    at.toggle[0].set_value(True).run()
    assert not at.exception
