import os
import csv
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# =====================
# ENV VAR
# =====================
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")

# =====================
# GLOBAL STATE
# =====================
WATCHLIST = []
SCRIP_MASTER = []

# =====================
# LOAD LOCAL SCRIP MASTER
# =====================
def load_scrip_master():
    path = os.path.join("data", "nse_eq_scrip_master.csv")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": r["exchange_token"],
                "trading_symbol": r["trading_symbol"],
                "company_name": r["company_name"]
            })

load_scrip_master()

# =====================
# ROUTES
# =====================
@app.route("/")
def index():
    return render_template("index.html")

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
    if stock and stock not in WATCHLIST:
        WATCHLIST.append(stock)
    return jsonify(WATCHLIST)

@app.route("/remove", methods=["POST"])
def remove():
    symbol = request.json["trading_symbol"]
    global WATCHLIST
    WATCHLIST = [s for s in WATCHLIST if s["trading_symbol"] != symbol]
    return jsonify(WATCHLIST)

@app.route("/prices")
def prices():
    if not WATCHLIST:
        return jsonify([])

    query = ",".join(
        f"nse_cm|{s['exchange_token']}" for s in WATCHLIST
    )

    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{query}/all"

    try:
        resp = requests.get(
            url,
            headers={"Authorization": ACCESS_TOKEN},
            timeout=5
        ).json()
    except Exception:
        return jsonify([])

    # Normalize response
    if isinstance(resp, dict) and "data" in resp:
        quotes = resp["data"]
    elif isinstance(resp, list):
        quotes = resp
    else:
        return jsonify([])

    if isinstance(quotes, dict):
        quotes = [quotes]

    result = []

    for stock, q in zip(WATCHLIST, quotes):
        try:
            ltp = float(q.get("ltp", 0))
            change = float(q.get("change", 0))
            prev_close = float(q.get("ohlc", {}).get("close", 0))
            open_p = float(q.get("ohlc", {}).get("open", 0))
            high = float(q.get("ohlc", {}).get("high", 0))
            low = float(q.get("ohlc", {}).get("low", 0))

            pct = (change / (prev_close or 1)) * 100

            result.append({
                "symbol": stock["trading_symbol"],
                "company": stock["company_name"],
                "ltp": round(ltp, 2),
                "change_pct": round(pct, 2),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(prev_close, 2)
            })
        except Exception:
            continue

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
