"""Dựng biểu đồ nến Plotly nhiều tầng: giá + chỉ báo, khối lượng, RSI/MACD."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

UP, DOWN = "#16a34a", "#dc2626"
BLUE, ORANGE, GREY, PURPLE = "#2b6cb0", "#dd8a1b", "#8a94a6", "#7c3aed"


def candle_fig(d: pd.DataFrame, title: str, *, show_sma: bool = True, show_bb: bool = True,
               panel: str = "RSI", uirev: str = "keep", height: int = 760) -> go.Figure:
    """`d` cần có cột time_local (giờ hiển thị), OHLCV và các cột chỉ báo. panel: 'RSI' | 'MACD' | 'Không'."""
    has_panel = panel in ("RSI", "MACD")
    rows = 3 if has_panel else 2
    heights = [0.62, 0.18, 0.20] if has_panel else [0.78, 0.22]
    f = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=heights)
    x = d["time_local"]
    up = d["close"] >= d["open"]

    # ---- Tầng 1: giá ----
    if show_bb:
        f.add_trace(go.Scatter(x=x, y=d["bb_up"], line=dict(width=0), hoverinfo="skip", showlegend=False), row=1, col=1)
        f.add_trace(go.Scatter(x=x, y=d["bb_low"], line=dict(width=0), fill="tonexty",
                               fillcolor="rgba(138,148,166,0.13)", name="Bollinger (20, 2σ)", hoverinfo="skip"),
                    row=1, col=1)
    f.add_trace(go.Candlestick(x=x, open=d["open"], high=d["high"], low=d["low"], close=d["close"], name="Giá",
                               increasing=dict(line=dict(color=UP), fillcolor=UP),
                               decreasing=dict(line=dict(color=DOWN), fillcolor=DOWN)), row=1, col=1)
    if show_sma:
        f.add_trace(go.Scatter(x=x, y=d["sma20"], name="SMA 20", line=dict(color=BLUE, width=1.8)), row=1, col=1)
        f.add_trace(go.Scatter(x=x, y=d["sma50"], name="SMA 50", line=dict(color=ORANGE, width=1.8)), row=1, col=1)

    last = d.iloc[-1]
    color = UP if last["close"] >= last["open"] else DOWN
    f.add_hline(y=last["close"], line=dict(color=color, width=1, dash="dot"), row=1, col=1)
    f.add_annotation(x=x.iloc[-1], y=last["close"], text=f"<b>{last['close']:,.2f}</b>", xanchor="left", xshift=6,
                     showarrow=False, bgcolor=color, font=dict(color="white", size=12), row=1, col=1)
    hi, lo = d.loc[d["high"].idxmax()], d.loc[d["low"].idxmin()]
    f.add_annotation(x=hi["time_local"], y=hi["high"], text=f"Đỉnh {hi['high']:,.2f}", showarrow=True, arrowhead=2,
                     ay=-28, ax=0, font=dict(size=11, color=UP), row=1, col=1)
    f.add_annotation(x=lo["time_local"], y=lo["low"], text=f"Đáy {lo['low']:,.2f}", showarrow=True, arrowhead=2,
                     ay=28, ax=0, font=dict(size=11, color=DOWN), row=1, col=1)

    # ---- Tầng 2: khối lượng ----
    f.add_trace(go.Bar(x=x, y=d["volume"], marker_color=np.where(up, UP, DOWN), opacity=0.75, name="Khối lượng",
                       showlegend=False), row=2, col=1)

    # ---- Tầng 3: RSI hoặc MACD ----
    if panel == "RSI":
        f.add_hrect(y0=70, y1=100, fillcolor="rgba(220,38,38,0.08)", line_width=0, row=3, col=1)
        f.add_hrect(y0=0, y1=30, fillcolor="rgba(22,163,74,0.08)", line_width=0, row=3, col=1)
        f.add_trace(go.Scatter(x=x, y=d["rsi14"], name="RSI 14", line=dict(color=PURPLE, width=2), showlegend=False),
                    row=3, col=1)
        for lv in (30, 70):
            f.add_hline(y=lv, line=dict(color=GREY, width=1, dash="dash"), row=3, col=1)
        if pd.notna(last["rsi14"]):
            f.add_annotation(x=x.iloc[-1], y=last["rsi14"], text=f"<b>{last['rsi14']:.1f}</b>", xanchor="left",
                             xshift=6, showarrow=False, bgcolor=PURPLE, font=dict(color="white", size=11), row=3, col=1)
        f.update_yaxes(title_text="RSI", range=[0, 100], tickvals=[30, 50, 70], row=3, col=1)
    elif panel == "MACD":
        f.add_trace(go.Bar(x=x, y=d["macd_hist"], marker_color=np.where(d["macd_hist"] >= 0, UP, DOWN),
                           opacity=0.6, name="Histogram", showlegend=False), row=3, col=1)
        f.add_trace(go.Scatter(x=x, y=d["macd"], name="MACD", line=dict(color=BLUE, width=1.8), showlegend=False), row=3, col=1)
        f.add_trace(go.Scatter(x=x, y=d["macd_signal"], name="Signal", line=dict(color=ORANGE, width=1.8), showlegend=False),
                    row=3, col=1)
        f.update_yaxes(title_text="MACD", row=3, col=1)

    f.update_yaxes(title_text="Giá (USD)", row=1, col=1)
    f.update_yaxes(title_text="Khối lượng", row=2, col=1)
    f.update_xaxes(rangeslider_visible=False, showgrid=True, gridcolor="#eef1f6")
    f.update_layout(template="plotly_white", height=height, hovermode="x unified", uirevision=uirev,
                    font=dict(family="Inter, Segoe UI, Arial", size=12), margin=dict(t=70, b=40, l=70, r=90),
                    title=dict(text=title, x=0.01, font=dict(size=18)), legend=dict(orientation="h", y=1.06, x=0))
    return f
