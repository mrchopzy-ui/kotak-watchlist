import os
import csv
import json
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
# SIMPLE SUPERTRAND LOGIC (15-MIN PROXY)
# =====================
def supertrend_signal(ltp, open_p, high, low):
    midpoint = (high + low) / 2

    if ltp > midpoint and ltp > open_p:
        return "BUY"
    elif ltp < midpoint and ltp < open_p:
        return "SELL"
    return "NEUTRAL"

# =====================
# ROUTES
# =====================
@app.route("/")
def index():
    return render_template(
        "index.html",
        tabs=WATCHLISTS.keys(),
        active=ACTIVE_TAB
    )

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
    return jsonify(list(WATCHLISTS.keys()))

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([
        s for s in SCRIP_MASTER
        if q in s["trading_symbol"].lower()
    ][:10])

@app.route("/add", methods=["POST"])
def add():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
        save_watchlists()
    return jsonify(WATCHLISTS[ACTIVE_TAB])

@app.route("/remove", methods=["POST"])
def remove():
    symbol = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != symbol
    ]
    save_watchlists()
    return jsonify(WATCHLISTS[ACTIVE_TAB])

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
        ltp = float(q.get("ltp", 0))
        open_p = float(ohlc.get("open", 0))
        high = float(ohlc.get("high", 0))
        low = float(ohlc.get("low", 0))
        close = float(ohlc.get("close", 1))
        change = float(q.get("change", 0))

        signal = supertrend_signal(ltp, open_p, high, low)

        out.append({
            "symbol": stock["trading_symbol"],
            "company": stock["company_name"],
            "ltp": round(ltp, 2),
            "change_pct": round((change / close) * 100, 2),
            "open": round(open_p, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "supertrend": signal
        })

    return jsonify(out)

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
