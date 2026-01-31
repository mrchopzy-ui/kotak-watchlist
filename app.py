import os
import csv
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# =====================
# ENV VARIABLES (Render-safe)
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

    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{query}/ltp"

    r = requests.get(
        url,
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    result = []
    for s, q in zip(WATCHLIST, r):
        ltp = float(q["ltp"])
        prev = ltp - float(q["change"])
        pct = (q["change"] / prev * 100) if prev else 0

        result.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "ltp": round(ltp, 2),
            "change_pct": round(pct, 2)
        })

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
