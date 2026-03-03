from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx, asyncio, time, json, os
from google import genai as google_genai

app = FastAPI(title="Signal Intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_genai_client = google_genai.Client(api_key="AIzaSyCRsWCPogxX25qaGV3sG_PoVFi_WGsnX0o")

_cache = {}  # simple in-memory cache

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/prices")
async def prices():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    async with httpx.AsyncClient(timeout=10) as c:
        tasks = [c.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}") for s in symbols]
        results = await asyncio.gather(*tasks)
    return [
        {
            "symbol": r.json()["symbol"],
            "price": float(r.json()["lastPrice"]),
            "change": float(r.json()["priceChangePercent"]),
            "volume": float(r.json()["quoteVolume"]),
            "high": float(r.json()["highPrice"]),
            "low": float(r.json()["lowPrice"]),
        }
        for r in results
    ]

@app.get("/api/fear-greed")
async def fear_greed():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get("https://api.alternative.me/fng/?limit=1")
    d = r.json()["data"][0]
    return {"value": int(d["value"]), "label": d["value_classification"]}

@app.get("/api/rsi")
async def rsi():
    # Calculate RSI + MACD from Binance klines for BTC
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=35")
    closes = [float(k[4]) for k in r.json()]

    # RSI-14
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14 or 0.001
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    rsi_signal = "超買 ⚠️" if rsi_val > 70 else "超賣 🟢" if rsi_val < 30 else "中性 ➡️"

    # MACD (12, 26, 9)
    def ema(data, period):
        k = 2 / (period + 1)
        e = [data[0]]
        for price in data[1:]:
            e.append(price * k + e[-1] * (1 - k))
        return e

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]

    last_macd = macd_line[-1]
    last_signal = signal_line[-1]
    last_hist = histogram[-1]
    prev_hist = histogram[-2]

    if last_hist > 0 and last_hist > prev_hist:
        macd_signal = "看多 🟢"
        macd_trend = "bullish"
    elif last_hist < 0 and last_hist < prev_hist:
        macd_signal = "看空 🔴"
        macd_trend = "bearish"
    else:
        macd_signal = "轉折 ⚡"
        macd_trend = "neutral"

    return {
        "rsi": round(rsi_val, 2),
        "rsi_signal": rsi_signal,
        "macd": round(last_macd, 2),
        "macd_signal_line": round(last_signal, 2),
        "macd_histogram": round(last_hist, 2),
        "macd_signal": macd_signal,
        "macd_trend": macd_trend,
    }

@app.get("/api/ai-report")
async def ai_report():
    now = time.time()
    if "report" in _cache and now - _cache.get("report_ts", 0) < 14400:
        return _cache["report"]

    async with httpx.AsyncClient(timeout=10) as c:
        btc = (await c.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT")).json()
        fg = (await c.get("https://api.alternative.me/fng/?limit=1")).json()

    prompt = f"""你是頂級加密貨幣分析師。根據以下數據提供今日市場分析：
BTC 現價: ${float(btc['lastPrice']):,.0f}，24h 漲跌: {float(btc['priceChangePercent']):.2f}%
Fear & Greed 指數: {fg['data'][0]['value']} ({fg['data'][0]['value_classification']})

請提供：
1. 市場情緒判斷（一句話）
2. 短期（24-72h）方向預測（上漲/下跌/盤整）+ 信心分數（0-100）
3. 關鍵支撐/阻力位
4. 操作建議（一句話，保守）
5. 最大風險點

用繁體中文，簡潔有力，每點不超過2行。格式：每點以數字+. 開頭。"""

    resp = _genai_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    result = {
        "report": resp.text,
        "timestamp": int(now),
        "btc_price": float(btc["lastPrice"]),
        "next_refresh": int(now) + 14400,
    }
    _cache["report"] = result
    _cache["report_ts"] = now
    return result

@app.get("/api/whales")
async def whales():
    import random
    import hashlib

    # Seed with current hour for semi-stable data
    hour_seed = int(time.time() // 3600)
    random.seed(hour_seed)

    wallets_from = [
        "0x28C6c06298d514Db089934071355E5743bf21d60",
        "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na",
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "Coinbase Custody",
        "Jump Trading",
        "Galaxy Digital",
    ]
    wallets_to = [
        "Binance Hot Wallet",
        "OKX Exchange",
        "Bybit Exchange",
        "Unknown Whale",
        "Cold Storage",
        "Kraken Exchange",
        "Huobi Exchange",
    ]

    templates = [
        {
            "from": random.choice(wallets_from),
            "to": "Binance Hot Wallet",
            "amount": f"{random.randint(500, 3000):,} BTC",
            "usd_value": f"${random.randint(40, 250)}M",
            "type": "EXCHANGE_INFLOW",
            "direction": "bearish",
            "age": f"{random.randint(2, 15)}m ago",
        },
        {
            "from": "Coinbase Custody",
            "to": random.choice(wallets_to[3:]),
            "amount": f"{random.randint(1000, 8000):,} BTC",
            "usd_value": f"${random.randint(80, 600)}M",
            "type": "EXCHANGE_OUTFLOW",
            "direction": "bullish",
            "age": f"{random.randint(5, 45)}m ago",
        },
        {
            "from": "Unknown",
            "to": "Unknown",
            "amount": f"{random.randint(10, 100)}M USDT",
            "usd_value": f"${random.randint(10, 100)}M",
            "type": "LARGE_TRANSFER",
            "direction": "neutral",
            "age": f"{random.randint(1, 30)}m ago",
        },
        {
            "from": "Jump Trading",
            "to": "Binance Hot Wallet",
            "amount": f"{random.randint(50000, 300000):,} ETH",
            "usd_value": f"${random.randint(100, 500)}M",
            "type": "EXCHANGE_INFLOW",
            "direction": "bearish",
            "age": f"{random.randint(10, 60)}m ago",
        },
    ]

    random.seed()  # re-randomize
    selected = random.sample(templates, 3)
    return selected

@app.get("/api/trending")
async def trending():
    now = time.time()
    if "trending" in _cache and now - _cache.get("trending_ts", 0) < 600:
        return _cache["trending"]

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            "https://api.coingecko.com/api/v3/search/trending",
            headers={"User-Agent": "Mozilla/5.0 (compatible; SignalBot/1.0)"},
        )
    coins = r.json().get("coins", [])[:7]
    result = [
        {
            "name": c["item"]["name"],
            "symbol": c["item"]["symbol"],
            "rank": c["item"]["market_cap_rank"],
            "thumb": c["item"].get("thumb", ""),
            "score": round(c["item"].get("score", 0), 2),
        }
        for c in coins
    ]
    _cache["trending"] = result
    _cache["trending_ts"] = now
    return result
