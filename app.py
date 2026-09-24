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
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    <style>
    .block-container {padding-top: 2.2rem;}
    /* Streamlit làm mờ dần (opacity/transition) các phần tử "cũ" mỗi khi fragment tự chạy lại
       (run_every) trong lúc chờ dữ liệu mới, gây cảm giác chớp/nhấp nháy dù giá chỉ đổi một chút.
       [data-stale] phủ vùng biểu đồ/KPI/bảng; [role=tab*] và details/summary phủ thêm tab + expander
       (hai khu vực này Streamlit không gắn data-stale nên phải chặn riêng). */
    [data-stale="true"], [data-stale="true"] * {opacity: 1 !important; transition: none !important;}
    [role="tablist"], [role="tab"] {opacity: 1 !important; transition: none !important;}
    details, summary {opacity: 1 !important;}
    div[data-testid="stElementContainer"], div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"] {transition: none !important;}

    /* ---- Tiêu đề & sidebar ---- */
    .app-title {display: flex; align-items: center; gap: .55rem; font-size: 1.9rem; font-weight: 800;
                margin: 0 0 .2rem;}
    .app-title i {color: #2b6cb0;}
    .sidebar-brand {display: flex; align-items: center; gap: .5rem; font-size: 1.35rem; font-weight: 800;
                    margin-bottom: .1rem;}
    .sidebar-brand i {color: #2b6cb0;}
    .sidebar-caption {display: flex; align-items: center; gap: .4rem; color: #6b7280; font-size: .85rem;
                      margin-bottom: .6rem;}
    .section-heading {display: flex; align-items: center; gap: .45rem; font-weight: 700; font-size: .95rem;
                      color: #374151; margin: .2rem 0 .5rem;}
    .section-heading i {color: #6b7280;}

    /* ---- Thẻ KPI ---- */
    .kpi-row {display: flex; gap: 10px; flex-wrap: wrap; margin: 4px 0 14px;}
    .kpi-card {flex: 1 1 150px; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
              padding: 10px 14px; box-shadow: 0 1px 2px rgba(0,0,0,.04);}
    .kpi-label {display: flex; align-items: center; gap: .4rem; color: #6b7280; font-weight: 700;
               font-size: .74rem; text-transform: uppercase; letter-spacing: .03em;}
    .kpi-value {font-size: 1.5rem; font-weight: 800; margin-top: 2px; line-height: 1.15;}
    .kpi-note {font-size: .78rem; color: #6b7280; margin-top: 2px;}
    .kpi-up {color: #16a34a;} .kpi-down {color: #dc2626;}

    /* ---- Banner cảnh báo dữ liệu mô phỏng ---- */
    .alert-sim {display: flex; align-items: flex-start; gap: .6rem; background: #fffbeb; border: 1px solid #fde68a;
               color: #92400e; border-radius: 10px; padding: .7rem .9rem; margin: .3rem 0 .8rem; font-size: .92rem;}
    .alert-sim i {font-size: 1.1rem; margin-top: .1rem;}

    /* ---- Dòng trạng thái cập nhật ---- */
    .status-row {display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap; color: #6b7280;
                font-size: .85rem; margin-top: .3rem;}
    .status-row span {display: flex; align-items: center; gap: .35rem;}
    .status-live {color: #16a34a;} .status-paused {color: #d97706;}
    .status-live i {animation: pulse 1.6s ease-in-out infinite;}
    @keyframes pulse {0%, 100% {opacity: 1;} 50% {opacity: .35;}}

    /* ---- Khối giải thích ---- */
    .about-h {display: flex; align-items: center; gap: .5rem; font-weight: 800; font-size: 1.15rem;
             margin: 1.1rem 0 .4rem; color: #1f2937;}
    .about-h i {color: #2b6cb0;}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi_card(icon: str, label: str, value: str, note: str = "", note_class: str = "") -> str:
    return (f'<div class="kpi-card"><div class="kpi-label"><i class="bi {icon}"></i>{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-note {note_class}">{note}</div></div>')


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


def reset_replay() -> None:
    st.session_state.cursor = 0


# ------------------------------------------------------------------ thanh điều khiển
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><i class="bi bi-graph-up-arrow"></i>Candlestick</div>'
               '<div class="sidebar-caption"><i class="bi bi-broadcast"></i>Real-time · Binance / Kraken API</div>',
               unsafe_allow_html=True)
    coin = st.selectbox("Đồng", list(SYMBOLS), help="BTC, ETH, SOL, XRP, DOGE (tính theo USD/USDT)")
    interval = st.selectbox("Khung nến", list(INTERVAL_MIN), help="Mỗi nến = 1 phút / 5 phút / 15 phút / 1 giờ")
    window = st.slider("Số nến hiển thị", 50, 300, 120, 10)

    st.divider()
    mode = st.radio("Chế độ dữ liệu", ["Live", "Replay"], horizontal=True,
                    help="Live: gọi API sàn liên tục. Replay: phát lại lịch sử thật, mỗi lần thêm vài nến.")
    refresh_s = st.slider("Chu kỳ cập nhật (giây)", 1, 10, 2)
    step = st.slider("Tốc độ Replay (nến/lần)", 1, 5, 1, disabled=(mode != "Replay"))
    paused = st.toggle("Tạm dừng cập nhật", value=False)
    st.button("Chạy lại Replay", icon=":material/replay:", on_click=reset_replay, disabled=(mode != "Replay"))

    st.divider()
    st.markdown('<div class="section-heading"><i class="bi bi-sliders"></i>Hiển thị</div>', unsafe_allow_html=True)
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
st.markdown(f'<div class="app-title"><i class="bi bi-graph-up-arrow"></i>Biểu đồ nến {coin}/USD Real-Time</div>',
           unsafe_allow_html=True)
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
        st.markdown('<div class="alert-sim"><i class="bi bi-exclamation-triangle-fill"></i>'
                   '<div><b>Không kết nối được API của Binance và Kraken, đang hiển thị DỮ LIỆU MÔ PHỎNG</b> '
                   '(không phải giá thị trường thật).</div></div>', unsafe_allow_html=True)
        with st.expander("Chi tiết lỗi kết nối"):
            st.code("\n".join(errors) or "(không có)")

    # ---- KPI ----
    last, first = d.iloc[-1], d.iloc[0]
    chg_win = (last["close"] / first["close"] - 1) * 100
    chg_c = (last["close"] / last["open"] - 1) * 100
    rsi = last["rsi14"]
    trend_up = bool(pd.notna(last["sma50"]) and last["sma20"] > last["sma50"])
    price_cls = "kpi-up" if chg_c >= 0 else "kpi-down"
    win_cls = "kpi-up" if chg_win >= 0 else "kpi-down"
    rsi_note = "quá mua" if pd.notna(rsi) and rsi > 70 else "quá bán" if pd.notna(rsi) and rsi < 30 else "trung tính"
    cards = [
        kpi_card("bi-cash-coin", f"{coin}/USD", f"{last['close']:,.2f}", f"{chg_c:+.2f}% nến này", price_cls),
        kpi_card("bi-arrow-left-right", "Biến động cửa sổ", f"{chg_win:+.2f}%", f"từ {first['close']:,.2f}", win_cls),
        kpi_card("bi-arrows-vertical", "Cao nhất / Thấp nhất", f"{d['high'].max():,.2f}",
                f"thấp nhất {d['low'].min():,.2f}"),
        kpi_card("bi-bar-chart-fill", "Khối lượng cửa sổ", f"{d['volume'].sum():,.1f}",
                f"nến cuối {last['volume']:,.2f}"),
        kpi_card("bi-activity", "RSI (14)", f"{rsi:.1f}" if pd.notna(rsi) else "-", rsi_note),
        kpi_card("bi-signpost-split-fill", "Xu hướng SMA20/50", "Tăng" if trend_up else "Giảm",
                "SMA20 > SMA50" if trend_up else "SMA20 < SMA50", "kpi-up" if trend_up else "kpi-down"),
    ]
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)

    # ---- Biểu đồ ----
    title = f"<b>{coin}/USD · nến {interval}</b>  ({mode.upper()} · {source})"
    fig = candle_fig(d, title, show_sma=show_sma, show_bb=show_bb, panel=panel, uirev=f"{coin}-{interval}-{mode}")
    st.plotly_chart(fig, key=f"chart-{coin}-{interval}-{mode}")

    now = pd.Timestamp.now(tz=tz).strftime("%H:%M:%S")
    state_icon = "bi-pause-circle-fill" if paused else "bi-record-circle-fill"
    state_cls = "status-paused" if paused else "status-live"
    state_txt = "đang tạm dừng" if paused else "đang cập nhật"
    st.markdown(
        f'<div class="status-row">'
        f'<span class="{state_cls}"><i class="bi {state_icon}"></i>{state_txt}</span>'
        f'<span><i class="bi bi-clock-history"></i>cập nhật lúc {now} ({tz})</span>'
        f'<span><i class="bi bi-hdd-network"></i>nguồn: <b>{source}</b></span>'
        f'<span><i class="bi bi-bar-chart-steps"></i>{len(d)} nến hiển thị</span>'
        f'</div>', unsafe_allow_html=True)

    # ---- Bảng dữ liệu + tải CSV ----
    with st.expander("📋 Bảng dữ liệu (nến mới nhất trước)"):
        show = d.drop(columns=["time", "open_time", "close_time"]).rename(columns={"time_local": "Thời gian"})
        st.dataframe(show.iloc[::-1].head(60), hide_index=True)
        st.download_button("Tải CSV (cửa sổ đang hiển thị)", show.to_csv(index=False).encode("utf-8"),
                           file_name=f"{coin}_{interval}_candles.csv", mime="text/csv", key="dl",
                           icon=":material/download:")


with tab_chart:
    run_every = None if paused else refresh_s
    st.fragment(run_every=run_every)(live_panel)(coin, interval, window, mode, step, paused, TIMEZONES[tz_label],
                                                  show_sma, show_bb, panel, allow_synth)

with tab_about:
    st.markdown('<div class="about-h"><i class="bi bi-lightbulb-fill"></i>Cách đọc biểu đồ nến</div>',
               unsafe_allow_html=True)
    st.markdown(
        """Thân nến là khoảng **Open → Close** (xanh: giá tăng trong khung nến, đỏ: giảm); bấc nến là **High/Low**.
Nến cuối cùng **đang hình thành** nên thân và bấc của nó thay đổi theo từng lần cập nhật."""
    )

    st.markdown('<div class="about-h"><i class="bi bi-graph-up"></i>Các chỉ báo</div>', unsafe_allow_html=True)
    st.markdown(
        """- **SMA20 cắt lên SMA50** thường được xem là tín hiệu xu hướng tăng; cắt xuống là giảm.
- **Dải Bollinger** giãn rộng khi biến động mạnh, thu hẹp khi thị trường đi ngang.
- **RSI > 70** là vùng quá mua, **RSI < 30** là quá bán. **MACD** đo động lượng qua chênh lệch hai đường EMA."""
    )

    st.markdown('<div class="about-h"><i class="bi bi-arrow-repeat"></i>Real-time hoạt động thế nào?</div>',
               unsafe_allow_html=True)
    st.markdown(
        """1. Khu vực biểu đồ là một **`st.fragment(run_every=...)`**: Streamlit tự chạy lại riêng khu vực này mỗi vài giây,
   không tải lại cả trang nên thanh điều khiển không bị giật.
2. Mỗi lần chạy lại, ứng dụng gọi **API công khai của sàn** (`get_klines`) và tính lại chỉ báo (`add_indicators`).
3. `st.cache_data(ttl=2)` giữ kết quả 2 giây để không vượt giới hạn tần suất của sàn.
4. **Replay** phát lại ~1000 nến lịch sử thật, mỗi lần thêm vài nến, hữu ích khi muốn demo ổn định."""
    )

    st.markdown('<div class="about-h"><i class="bi bi-database-fill"></i>Nguồn dữ liệu</div>', unsafe_allow_html=True)
    st.markdown(
        """| Ưu tiên | Nguồn |
|---|---|
| 1 | Binance Market Data API (`data-api.binance.vision`) |
| 2 | Kraken Public API (`api.kraken.com`) |
| 3 | Dữ liệu **mô phỏng**, chỉ khi cả hai sàn lỗi (luôn có cảnh báo) |

> Ứng dụng phục vụ học tập về trực quan hóa dữ liệu, **không phải khuyến nghị đầu tư**."""
    )
