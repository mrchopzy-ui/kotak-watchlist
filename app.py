import os
import csv
import json
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")

DATA_DIR = "data"
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlists.json")

SCRIP_MASTER = []

# ---------------- LOAD SCRIP MASTER ----------------
def load_scrip_master():
    with open(os.path.join(DATA_DIR, "nse_eq_scrip_master.csv"), newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": r["exchange_token"],
                "trading_symbol": r["trading_symbol"],
                "company_name": r["company_name"]
            })

# ---------------- WATCHLIST STORAGE ----------------
def load_watchlists():
    if not os.path.exists(WATCHLIST_FILE):
        return {"Watchlist 1": []}
    with open(WATCHLIST_FILE, "r") as f:
        return json.load(f)

def save_watchlists(data):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

load_scrip_master()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tabs")
def tabs():
    return jsonify(list(load_watchlists().keys()))

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIP_MASTER if q in s["trading_symbol"].lower()][:10])

@app.route("/watchlist/<tab>")
def get_watchlist(tab):
    return jsonify(load_watchlists().get(tab, []))

@app.route("/add", methods=["POST"])
def add():
    data = request.json
    tab = data["tab"]
    stock = data["stock"]

    wl = load_watchlists()
    wl.setdefault(tab, [])

    if stock not in wl[tab]:
        wl[tab].append(stock)

    save_watchlists(wl)
    return jsonify(wl[tab])

@app.route("/remove", methods=["POST"])
def remove():
    tab = request.json["tab"]
    symbol = request.json["symbol"]

    wl = load_watchlists()
    wl[tab] = [s for s in wl[tab] if s["trading_symbol"] != symbol]
    save_watchlists(wl)
    return jsonify(wl[tab])

@app.route("/prices/<tab>")
def prices(tab):
    wl = load_watchlists().get(tab, [])
    if not wl:
        return jsonify([])

    query = ",".join(f"nse_cm|{s['exchange_token']}" for s in wl)
    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{query}/all"

    resp = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()
    quotes = resp.get("data", resp)
    if isinstance(quotes, dict):
        quotes = [quotes]

    out = []
    for s, q in zip(wl, quotes):
        ohlc = q.get("ohlc", {})
        ltp = float(q.get("ltp", 0))
        prev = float(ohlc.get("close", 0))
        change = ltp - prev if prev else 0
        pct = (change / prev * 100) if prev else 0

        out.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "ltp": round(ltp, 2),
            "change_pct": round(pct, 2),
            "open": round(float(ohlc.get("open", 0)), 2),
            "high": round(float(ohlc.get("high", 0)), 2),
            "low": round(float(ohlc.get("low", 0)), 2),
            "close": round(prev, 2)
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
