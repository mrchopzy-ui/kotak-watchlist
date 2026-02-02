from flask import Flask, render_template, jsonify, request
import csv
import os
import requests

app = Flask(__name__)

DATA_FILE = "data/nse_eq_scrip_master.csv"

WATCHLISTS = {"Watchlist 1": []}
ACTIVE_TAB = "Watchlist 1"

SCRIPS = []

# ---------------- LOAD SCRIP MASTER ----------------

def load_scrip_master():
    global SCRIPS
    if not os.path.exists(DATA_FILE):
        print("❌ nse_eq_scrip_master.csv not found")
        exit(1)

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        SCRIPS = list(reader)

    if not SCRIPS:
        print("❌ Local scrip master is empty")
        exit(1)

    print(f"✅ Loaded {len(SCRIPS)} EQ stocks")

load_scrip_master()

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        tabs=WATCHLISTS.keys(),
        active=ACTIVE_TAB
    )

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([
        s for s in SCRIPS
        if q in s["trading_symbol"].lower()
    ][:10])

@app.route("/add", methods=["POST"])
def add_stock():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    symbol = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != symbol
    ]
    return "", 204

@app.route("/prices")
def prices():
    result = []

    for s in WATCHLISTS[ACTIVE_TAB]:
        # Dummy prices (replace with Kotak Quotes later)
        result.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],   # ✅ FIX HERE
            "ltp": 123.45,
            "change_pct": 1.23,
            "open": 120.00,
            "high": 125.00,
            "low": 119.50,
            "close": 121.00
        })

    return jsonify(result)

@app.route("/new-tab", methods=["POST"])
def new_tab():
    name = request.json["name"]
    if name not in WATCHLISTS:
        WATCHLISTS[name] = []
    return "", 204

@app.route("/set-tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return "", 204

if __name__ == "__main__":
    app.run(debug=True)
