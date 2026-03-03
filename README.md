# 📊 Signal Intelligence Terminal

**signal.iamblwb.com** — 暗黑終端機風格的加密貨幣情報 Dashboard

## 功能

| 功能 | 說明 |
|------|------|
| 📈 市場概覽 | BTC/ETH/SOL/BNB 即時價格 + 24h 漲跌幅 |
| 😱 Fear & Greed 指數 | 大圓弧儀表板，0-100 分（極度恐慌 → 極度貪婪）|
| 📊 技術指標 | RSI + MACD 信號（超買/超賣/中性）|
| 🤖 AI 預測報告 | Gemini 2.5 Flash 每4小時更新市場分析 |
| 🐳 鯨魚警報 | 大額轉帳追蹤（Glassnode-style 模擬）|
| 🔥 熱門幣種 | CoinGecko trending API 即時排行 |

## 技術架構

- **後端**: FastAPI (Python 3.11), port 8006
- **前端**: 純 HTML + 暗黑終端機風格 CSS + Matrix 雨背景
- **AI**: Google Gemini 2.5 Flash API
- **免費 API**: Binance · Fear & Greed Index · CoinGecko
- **部署**: systemd user service + nginx reverse proxy + Let's Encrypt SSL

## 本地開發

```bash
cd backend
uvicorn main:app --reload --port 8006
```

## License

MIT
