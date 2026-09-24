# 📈 Candlestick Real-Time

Ứng dụng web **biểu đồ nến (candlestick) tự cập nhật theo thời gian thực**, xây dựng bằng **Streamlit + Plotly**, dữ liệu lấy trực tiếp từ API công khai của sàn giao dịch (Binance, dự phòng Kraken). Đây là bản chuyển từ notebook Google Colab của bài *Plotly Real-Time Update* thành ứng dụng trực tuyến để triển khai qua **GitHub + Streamlit Community Cloud**.

> Ứng dụng phục vụ học tập về trực quan hóa dữ liệu, **không phải khuyến nghị đầu tư**.

## Tính năng

- Biểu đồ nến 3 tầng: giá (nến, SMA 20/50, dải Bollinger, nhãn giá hiện tại, số đỉnh/đáy), khối lượng, và RSI hoặc MACD.
- **Live**: gọi API sàn mỗi 1–10 giây, nến cuối cùng nhảy theo giá thật. **Replay**: phát lại ~1000 nến lịch sử thật.
- 6 thẻ KPI (giá, biến động, cao/thấp, khối lượng, RSI, xu hướng SMA), bảng dữ liệu và nút tải CSV.
- Chọn đồng (BTC, ETH, SOL, XRP, DOGE), khung nến (1m, 5m, 15m, 1h), số nến, múi giờ, bật/tắt chỉ báo, tạm dừng.
- Tự chuyển nguồn Binance → Kraken khi bị chặn; nếu cả hai lỗi sẽ hiện **dữ liệu mô phỏng kèm cảnh báo rõ ràng**.

## Cấu trúc dự án

```
candlestick-realtime/
├── app.py                  # Giao diện Streamlit (sidebar, KPI, fragment tự làm mới)
├── core/
│   ├── data.py             # Tải nến Binance/Kraken, dữ liệu mô phỏng dự phòng
│   ├── indicators.py       # SMA, EMA, MACD, Bollinger, RSI, ...
│   └── charts.py           # Dựng biểu đồ nến Plotly
├── tests/                  # pytest (dữ liệu, chỉ báo, biểu đồ, chạy thử toàn app)
├── .streamlit/config.toml  # Theme
├── .github/workflows/ci.yml# GitHub Actions: chạy test khi push / pull request
├── requirements.txt
└── requirements-dev.txt
```

## Chạy trên máy

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Mở http://localhost:8501.

## Chạy test

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Đưa lên GitHub và triển khai trực tuyến

**Bước 1 – Tạo repo GitHub và đẩy code**

1. Vào https://github.com/new, tạo repository (ví dụ `candlestick-realtime`), để trống (không thêm README/.gitignore).
2. Trong thư mục dự án:

```bash
git init
git add .
git commit -m "Candlestick real-time app"
git branch -M main
git remote add origin https://github.com/<ten-tai-khoan>/candlestick-realtime.git
git push -u origin main
```

Sau khi push, tab **Actions** trên GitHub sẽ tự chạy test (file `ci.yml`).

**Bước 2 – Triển khai bằng Streamlit Community Cloud (miễn phí)**

1. Vào https://share.streamlit.io và đăng nhập bằng tài khoản GitHub.
2. Bấm **Create app** → **Deploy a public app from GitHub**.
3. Chọn repository `candlestick-realtime`, nhánh `main`, **Main file path** là `app.py`.
4. (Tùy chọn) Trong **Advanced settings** chọn Python 3.11 hoặc 3.12.
5. Bấm **Deploy**. Sau 1–2 phút bạn có đường link dạng `https://<ten-app>.streamlit.app` để chia sẻ.

Mỗi lần `git push` lên `main`, Streamlit Cloud tự cập nhật ứng dụng. Ứng dụng **không cần API key hay secrets**.

## Lưu ý kỹ thuật

- **Real-time** dùng `st.fragment(run_every=...)`: chỉ khu vực biểu đồ chạy lại theo chu kỳ, thanh điều khiển không bị tải lại. Cần Streamlit ≥ 1.37.
- **Bộ nhớ đệm** `st.cache_data(ttl=2)` giữ kết quả 2 giây để không vượt giới hạn tần suất của sàn.
- Máy chủ Streamlit Cloud đặt tại Mỹ nên **Binance có thể bị chặn theo khu vực**; ứng dụng tự dùng Kraken. Tên nguồn đang dùng luôn hiển thị dưới biểu đồ.
- Nhiều người mở app cùng lúc sẽ cùng gọi API; bộ nhớ đệm dùng chung giữa các phiên nên số lần gọi thực tế vẫn thấp.

## Mở rộng

- **Thêm đồng coin**: thêm dòng vào `SYMBOLS` trong `core/data.py` (mã Binance, mã Kraken) và giá cơ sở vào `SYNTHETIC_BASE`.
- **Đổi sang cổ phiếu**: viết thêm hàm `fetch_<nguon>()` trả về DataFrame đúng các cột trong `COLUMNS` (ví dụ dùng `yfinance` cho cổ phiếu Mỹ) rồi thêm vào vòng lặp của `get_klines`. Cổ phiếu chỉ có dữ liệu mới khi sàn mở cửa; ngoài giờ hãy dùng chế độ Replay.
- **Thêm chỉ báo**: bổ sung vào `add_indicators` (`core/indicators.py`) và vẽ trong `candle_fig` (`core/charts.py`).

## Nguồn dữ liệu

- Binance Spot API: https://developers.binance.com/docs/binance-spot-api-docs
- Kraken REST API: https://docs.kraken.com/api/

## Giấy phép

MIT.
