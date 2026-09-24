"""Ứng dụng Streamlit: Biểu đồ nến (Candlestick) Real-Time.

Chạy cục bộ:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.charts import candle_fig
from core.data import INTERVAL_MIN, SYMBOLS, get_klines
from core.indicators import add_indicators

st.set_page_config(page_title="Candlestick Real-Time", page_icon="📈", layout="wide")

TIMEZONES = {"Việt Nam (UTC+7)": "Asia/Ho_Chi_Minh", "UTC": "UTC", "Tokyo (UTC+9)": "Asia/Tokyo",
             "New York": "America/New_York"}

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {font-size: 1.55rem; font-weight: 800;}
    [data-testid="stMetricLabel"] {color: #6b7280; font-weight: 600;}
    .block-container {padding-top: 2.2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ dữ liệu (có bộ nhớ đệm)
@st.cache_data(ttl=2, show_spinner=False)
def load_live(coin: str, interval: str, limit: int, allow_synthetic: bool):
    """Live: gọi API sàn, dùng lại kết quả trong 2 giây để không vượt giới hạn tần suất."""
    r = get_klines(coin, interval, limit, allow_synthetic=allow_synthetic)
    return r.df, r.source, r.errors


@st.cache_data(ttl=900, show_spinner="Đang tải lịch sử nến...")
def load_archive(coin: str, interval: str, allow_synthetic: bool):
    """Replay: tải ~1000 nến lịch sử một lần rồi phát lại."""
    r = get_klines(coin, interval, 1000, allow_synthetic=allow_synthetic)
    return r.df, r.source, r.errors


def metric(col, label: str, value: str, note: str | None = None, *, delta_color: str = "off", arrow: bool = False) -> None:
    """st.metric có ghi chú phụ; ẩn mũi tên (delta_arrow) khi ghi chú chỉ là chữ, tương thích cả bản Streamlit cũ."""
    try:
        col.metric(label, value, note, delta_color=delta_color, delta_arrow="auto" if arrow else "off")
    except TypeError:                                            # bản Streamlit cũ chưa có delta_arrow
        col.metric(label, value, note, delta_color=delta_color)


def reset_replay() -> None:
    st.session_state.cursor = 0


# ------------------------------------------------------------------ thanh điều khiển
with st.sidebar:
    st.title("📈 Candlestick")
    st.caption("Real-time · Binance / Kraken API")
    coin = st.selectbox("Đồng", list(SYMBOLS), help="BTC, ETH, SOL, XRP, DOGE (tính theo USD/USDT)")
    interval = st.selectbox("Khung nến", list(INTERVAL_MIN), help="Mỗi nến = 1 phút / 5 phút / 15 phút / 1 giờ")
    window = st.slider("Số nến hiển thị", 50, 300, 120, 10)

    st.divider()
    mode = st.radio("Chế độ dữ liệu", ["Live", "Replay"], horizontal=True,
                    help="Live: gọi API sàn liên tục. Replay: phát lại lịch sử thật, mỗi lần thêm vài nến.")
    refresh_s = st.slider("Chu kỳ cập nhật (giây)", 1, 10, 2)
    step = st.slider("Tốc độ Replay (nến/lần)", 1, 5, 1, disabled=(mode != "Replay"))
    paused = st.toggle("Tạm dừng cập nhật", value=False)
    st.button("Chạy lại Replay", on_click=reset_replay, disabled=(mode != "Replay"))

    st.divider()
    st.subheader("Hiển thị")
    show_sma = st.checkbox("Đường SMA 20 / 50", value=True)
    show_bb = st.checkbox("Dải Bollinger", value=True)
    panel = st.selectbox("Chỉ báo tầng dưới", ["RSI", "MACD", "Không"])
    tz_label = st.selectbox("Múi giờ", list(TIMEZONES))
    allow_synth = st.checkbox("Cho phép dữ liệu mô phỏng khi API lỗi", value=True,
                              help="Nếu cả Binance và Kraken đều không truy cập được, hiển thị dữ liệu MÔ PHỎNG "
                                   "(có cảnh báo rõ ràng) để giao diện vẫn chạy.")

# Đổi đồng/khung nến/chế độ thì đặt lại con trỏ Replay
cfg_key = (coin, interval, mode)
if st.session_state.get("cfg_key") != cfg_key:
    st.session_state.cfg_key = cfg_key
    st.session_state.cursor = 0

# ------------------------------------------------------------------ giao diện chính
st.title(f"Biểu đồ nến {coin}/USD Real-Time")
tab_chart, tab_about = st.tabs(["📊 Biểu đồ", "ℹ️ Giải thích"])


def live_panel(coin: str, interval: str, window: int, mode: str, step: int, paused: bool, tz: str,
               show_sma: bool, show_bb: bool, panel: str, allow_synth: bool) -> None:
    """Khu vực tự làm mới (fragment): lấy nến mới, tính chỉ báo, vẽ lại biểu đồ, KPI và bảng."""
    warm = window + 60                                            # nến "khởi động" để SMA50/RSI đúng ngay từ đầu
    try:
        if mode == "Live":
            raw, source, errors = load_live(coin, interval, warm, allow_synth)
        else:
            arch, source, errors = load_archive(coin, interval, allow_synth)
            n = st.session_state.get("cursor", 0)
            span = max(1, len(arch) - warm + 1)
            raw = arch.iloc[: warm + n % span] if len(arch) > warm else arch      # hết dữ liệu thì quay vòng
            if not paused:
                st.session_state.cursor = n + step
    except Exception as e:                                        # noqa: BLE001
        st.error(f"Không tải được dữ liệu: {e}")
        return

    d = add_indicators(raw).tail(window).reset_index(drop=True)
    d["time_local"] = d["time"].dt.tz_localize("UTC").dt.tz_convert(tz).dt.tz_localize(None)

    if source == "Mô phỏng":
        st.warning("⚠️ **Không kết nối được API của Binance và Kraken, đang hiển thị DỮ LIỆU MÔ PHỎNG** "
                   "(không phải giá thị trường thật).")
        with st.expander("Chi tiết lỗi kết nối"):
            st.code("\n".join(errors) or "(không có)")

    # ---- KPI ----
    last, first = d.iloc[-1], d.iloc[0]
    chg_win = (last["close"] / first["close"] - 1) * 100
    chg_c = (last["close"] / last["open"] - 1) * 100
    rsi = last["rsi14"]
    trend_up = bool(pd.notna(last["sma50"]) and last["sma20"] > last["sma50"])
    cols = st.columns(6)
    metric(cols[0], f"{coin}/USD", f"{last['close']:,.2f}", f"{chg_c:+.2f}% nến này", delta_color="normal", arrow=True)
    metric(cols[1], "Biến động cửa sổ", f"{chg_win:+.2f}%", f"từ {first['close']:,.2f}")
    metric(cols[2], "Cao nhất", f"{d['high'].max():,.2f}", f"thấp nhất {d['low'].min():,.2f}")
    metric(cols[3], "Khối lượng cửa sổ", f"{d['volume'].sum():,.1f}", f"nến cuối {last['volume']:,.2f}")
    metric(cols[4], "RSI (14)", f"{rsi:.1f}" if pd.notna(rsi) else "-",
           "quá mua" if rsi > 70 else "quá bán" if rsi < 30 else "trung tính")
    metric(cols[5], "Xu hướng SMA20/50", "Tăng" if trend_up else "Giảm", "SMA20 > SMA50" if trend_up else "SMA20 < SMA50")

    # ---- Biểu đồ ----
    title = f"<b>{coin}/USD · nến {interval}</b>  ({mode.upper()} · {source})"
    fig = candle_fig(d, title, show_sma=show_sma, show_bb=show_bb, panel=panel, uirev=f"{coin}-{interval}-{mode}")
    st.plotly_chart(fig, key=f"chart-{coin}-{interval}-{mode}")

    now = pd.Timestamp.now(tz=tz).strftime("%H:%M:%S")
    state = "⏸ đang tạm dừng" if paused else "🟢 đang cập nhật"
    st.caption(f"{state} · lần cập nhật gần nhất {now} ({tz}) · nguồn: **{source}** · {len(d)} nến hiển thị")

    # ---- Bảng dữ liệu + tải CSV ----
    with st.expander("Bảng dữ liệu (nến mới nhất trước)"):
        show = d.drop(columns=["time", "open_time", "close_time"]).rename(columns={"time_local": "Thời gian"})
        st.dataframe(show.iloc[::-1].head(60), hide_index=True)
        st.download_button("⬇️ Tải CSV (cửa sổ đang hiển thị)", show.to_csv(index=False).encode("utf-8"),
                           file_name=f"{coin}_{interval}_candles.csv", mime="text/csv", key="dl")


with tab_chart:
    run_every = None if paused else refresh_s
    st.fragment(run_every=run_every)(live_panel)(coin, interval, window, mode, step, paused, TIMEZONES[tz_label],
                                                  show_sma, show_bb, panel, allow_synth)

with tab_about:
    st.markdown(
        """
### Cách đọc biểu đồ nến
Thân nến là khoảng **Open → Close** (xanh: giá tăng trong khung nến, đỏ: giảm); bấc nến là **High/Low**.
Nến cuối cùng **đang hình thành** nên thân và bấc của nó thay đổi theo từng lần cập nhật.

### Các chỉ báo
- **SMA20 cắt lên SMA50** thường được xem là tín hiệu xu hướng tăng; cắt xuống là giảm.
- **Dải Bollinger** giãn rộng khi biến động mạnh, thu hẹp khi thị trường đi ngang.
- **RSI > 70** là vùng quá mua, **RSI < 30** là quá bán. **MACD** đo động lượng qua chênh lệch hai đường EMA.

### Real-time hoạt động thế nào?
1. Khu vực biểu đồ là một **`st.fragment(run_every=...)`**: Streamlit tự chạy lại riêng khu vực này mỗi vài giây,
   không tải lại cả trang nên thanh điều khiển không bị giật.
2. Mỗi lần chạy lại, ứng dụng gọi **API công khai của sàn** (`get_klines`) và tính lại chỉ báo (`add_indicators`).
3. `st.cache_data(ttl=2)` giữ kết quả 2 giây để không vượt giới hạn tần suất của sàn.
4. **Replay** phát lại ~1000 nến lịch sử thật, mỗi lần thêm vài nến, hữu ích khi muốn demo ổn định.

### Nguồn dữ liệu
| Ưu tiên | Nguồn |
|---|---|
| 1 | Binance Market Data API (`data-api.binance.vision`) |
| 2 | Kraken Public API (`api.kraken.com`) |
| 3 | Dữ liệu **mô phỏng**, chỉ khi cả hai sàn lỗi (luôn có cảnh báo) |

> Ứng dụng phục vụ học tập về trực quan hóa dữ liệu, **không phải khuyến nghị đầu tư**.
        """
    )
