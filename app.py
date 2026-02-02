from flask import Flask, render_template, request, jsonify
import os
import csv
import requests

app = Flask(__name__)

# ---------------- CONFIG ----------------
WATCHLISTS = {"Watchlist 1": []}
ACTIVE_TAB = "Watchlist 1"

SCRIP_MASTER = []
SCRIP_PATH = "data/nse_eq_scrip_master.csv"

# ---------------- LOAD SCRIP MASTER ----------------
def load_scrip_master():
    global SCRIP_MASTER
    if not os.path.exists(SCRIP_PATH):
        print("❌ Local scrip master not found")
        return

    with open(SCRIP_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        SCRIP_MASTER = list(reader)

    if not SCRIP_MASTER:
        print("❌ Local scrip master is empty")
    else:
        print(f"✅ Loaded {len(SCRIP_MASTER)} stocks")

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
    q = request.args.get("q", "").upper()
    results = [
        s for s in SCRIP_MASTER
        if q in s["trading_symbol"]
    ][:10]
    return jsonify(results)

@app.route("/add", methods=["POST"])
def add_stock():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
    return jsonify({"ok": True})

@app.route("/remove", methods=["POST"])
def remove_stock():
    symbol = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != symbol
    ]
    return jsonify({"ok": True})

@app.route("/prices")
def prices():
    data = []
    for s in WATCHLISTS[ACTIVE_TAB]:
        data.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "ltp": round(float(s.get("ltp", 0)), 2),
            "change_pct": round(float(s.get("change_pct", 0)), 2),
            "open": round(float(s.get("open", 0)), 2),
            "high": round(float(s.get("high", 0)), 2),
            "low": round(float(s.get("low", 0)), 2),
            "close": round(float(s.get("close", 0)), 2),
        })
    return jsonify(data)

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
    return jsonify({"ok": True})

@app.route("/rename-tab", methods=["POST"])
def rename_tab():
    global ACTIVE_TAB
    old = request.json["old"]
    new = request.json["new"]

    if old in WATCHLISTS and new not in WATCHLISTS:
        WATCHLISTS[new] = WATCHLISTS.pop(old)
        if ACTIVE_TAB == old:
            ACTIVE_TAB = new

    return jsonify({"ok": True})

# ---------------- START ----------------
if __name__ == "__main__":
    load_scrip_master()
    app.run(debug=True)
