import os
import csv
import json
import time
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")

DATA_DIR = "data"
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlists.json")

# =====================
# LOAD / SAVE WATCHLISTS
# =====================
def load_watchlists():
    if not os.path.exists(WATCHLIST_FILE):
        return {"Watchlist 1": []}
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_watchlists():
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(WATCHLISTS, f, indent=2)

WATCHLISTS = load_watchlists()
ACTIVE_TAB = list(WATCHLISTS.keys())[0]

# =====================
# LOAD SCRIP MASTER
# =====================
SCRIP_MASTER = []

def load_scrip_master():
    path = os.path.join(DATA_DIR, "nse_eq_scrip_master.csv")
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": r["exchange_token"],
                "trading_symbol": r["trading_symbol"],
                "company_name": r["company_name"]
            })

load_scrip_master()

# =====================
# SUPER TREND (15m)
# =====================
SUPER_CACHE = {}

def supertrend_15m(exchange_token):
    now = time.time()
    if exchange_token in SUPER_CACHE and now - SUPER_CACHE[exchange_token]["ts"] < 120:
        return SUPER_CACHE[exchange_token]["signal"]

    url = f"https://mis.kotaksecurities.com/script-details/1.0/intraday/candle"
    params = {
        "exchange": "nse_cm",
        "token": exchange_token,
        "interval": "15minute"
    }

    r = requests.get(url, params=params, headers={
        "Authorization": ACCESS_TOKEN
    }).json()

    candles = r.get("data", [])
    if len(candles) < 20:
        return "NA"

    highs, lows, closes = [], [], []
    for c in candles[-20:]:
        highs.append(float(c["high"]))
        lows.append(float(c["low"]))
        closes.append(float(c["close"]))

    # ATR(10)
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)

    atr = sum(trs[-10:]) / 10
    multiplier = 3

    upper = (highs[-1] + lows[-1]) / 2 + multiplier * atr
    lower = (highs[-1] + lows[-1]) / 2 - multiplier * atr

    signal = "BUY" if closes[-1] > upper else "SELL"

    SUPER_CACHE[exchange_token] = {
        "signal": signal,
        "ts": now
    }

    return signal

# =====================
# ROUTES
# =====================
@app.route("/")
def index():
    return render_template("index.html", tabs=WATCHLISTS.keys(), active=ACTIVE_TAB)

@app.route("/set-tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return jsonify(ok=True)

@app.route("/new-tab", methods=["POST"])
def new_tab():
    name = request.json["name"]
    if name not in WATCHLISTS:
        WATCHLISTS[name] = []
        save_watchlists()
    return jsonify(ok=True)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIP_MASTER if q in s["trading_symbol"].lower()][:10])

@app.route("/add", methods=["POST"])
def add():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
        save_watchlists()
    return jsonify(ok=True)

@app.route("/remove", methods=["POST"])
def remove():
    sym = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB] if s["trading_symbol"] != sym
    ]
    save_watchlists()
    return jsonify(ok=True)

@app.route("/prices")
def prices():
    wl = WATCHLISTS.get(ACTIVE_TAB, [])
    if not wl:
        return jsonify([])

    query = ",".join(f"nse_cm|{s['exchange_token']}" for s in wl)
    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{query}/all"

    r = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()
    quotes = r["data"] if isinstance(r, dict) else r
    if isinstance(quotes, dict):
        quotes = [quotes]

    out = []
    for stock, q in zip(wl, quotes):
        ohlc = q.get("ohlc", {})
        prev = float(ohlc.get("close", 1))
        change = float(q.get("change", 0))

        out.append({
            "symbol": stock["trading_symbol"],
            "company": stock["company_name"],
            "ltp": round(float(q.get("ltp", 0)), 2),
            "change_pct": round((change / prev) * 100, 2),
            "open": round(float(ohlc.get("open", 0)), 2),
            "high": round(float(ohlc.get("high", 0)), 2),
            "low": round(float(ohlc.get("low", 0)), 2),
            "close": round(prev, 2),
            "supertrend": supertrend_15m(stock["exchange_token"])
        })

    return jsonify(out)

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
