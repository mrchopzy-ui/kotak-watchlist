import os
import csv
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")

# =====================
# GLOBAL STATE
# =====================
WATCHLISTS = {
    "Watchlist 1": []
}
ACTIVE_TAB = "Watchlist 1"
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
    return render_template(
        "index.html",
        tabs=WATCHLISTS.keys(),
        active=ACTIVE_TAB
    )

@app.route("/set-tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return jsonify({"ok": True})

@app.route("/new-tab", methods=["POST"])
def new_tab():
    name = request.json["name"]
    if name not in WATCHLISTS:
        WATCHLISTS[name] = []
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
    return jsonify(WATCHLISTS[ACTIVE_TAB])

@app.route("/remove", methods=["POST"])
def remove():
    symbol = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != symbol
    ]
    return jsonify(WATCHLISTS[ACTIVE_TAB])

@app.route("/prices")
def prices():
    wl = WATCHLISTS[ACTIVE_TAB]
    if not wl:
        return jsonify([])

    query = ",".join(
        f"nse_cm|{s['exchange_token']}" for s in wl
    )

    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{query}/all"

    resp = requests.get(
        url,
        headers={"Authorization": ACCESS_TOKEN},
        timeout=5
    ).json()

    if isinstance(resp, dict) and "data" in resp:
        quotes = resp["data"]
    else:
        quotes = resp

    if isinstance(quotes, dict):
        quotes = [quotes]

    out = []

    for stock, q in zip(wl, quotes):
        ohlc = q.get("ohlc", {})
        change = float(q.get("change", 0))
        prev = float(ohlc.get("close", 1))

        out.append({
            "symbol": stock["trading_symbol"],
            "company": stock["company_name"],
            "ltp": round(float(q.get("ltp", 0)), 2),
            "change_pct": round((change / prev) * 100, 2),
            "open": round(float(ohlc.get("open", 0)), 2),
            "high": round(float(ohlc.get("high", 0)), 2),
            "low": round(float(ohlc.get("low", 0)), 2),
            "close": round(prev, 2)
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
