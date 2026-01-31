import os
import csv
import json
import requests
import pandas as pd
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
    with open(os.path.join(DATA_DIR, "nse_eq_scrip_master.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": r["exchange_token"],
                "trading_symbol": r["trading_symbol"],
                "company_name": r["company_name"]
            })

load_scrip_master()

# =====================
# SUPER TREND LOGIC
# =====================
def calculate_supertrend(df, period=10, multiplier=3):
    df["H-L"] = abs(df["high"] - df["low"])
    df["H-PC"] = abs(df["high"] - df["close"].shift())
    df["L-PC"] = abs(df["low"] - df["close"].shift())
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(period).mean()

    hl2 = (df["high"] + df["low"]) / 2
    df["upper"] = hl2 + multiplier * df["ATR"]
    df["lower"] = hl2 - multiplier * df["ATR"]

    df["supertrend"] = True
    for i in range(1, len(df)):
        if df["close"][i] > df["upper"][i-1]:
            df.at[i, "supertrend"] = True
        elif df["close"][i] < df["lower"][i-1]:
            df.at[i, "supertrend"] = False
        else:
            df.at[i, "supertrend"] = df["supertrend"][i-1]

    return "Buy" if df["supertrend"].iloc[-1] else "Sell"

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
    return jsonify(list(WATCHLISTS.keys()))

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
    return jsonify(WATCHLISTS[ACTIVE_TAB])

@app.route("/remove", methods=["POST"])
def remove():
    symbol = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [s for s in WATCHLISTS[ACTIVE_TAB] if s["trading_symbol"] != symbol]
    save_watchlists()
    return jsonify(WATCHLISTS[ACTIVE_TAB])

@app.route("/prices")
def prices():
    wl = WATCHLISTS.get(ACTIVE_TAB, [])
    if not wl:
        return jsonify([])

    out = []
    for s in wl:
        # 🔴 Kotak Intraday Candle API (15 min)
        url = f"https://mis.kotaksecurities.com/script-details/1.0/ohlc/{s['exchange']}|{s['exchange_token']}/15minute"
        candles = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

        df = pd.DataFrame(candles["data"])
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        signal = calculate_supertrend(df)

        out.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "supertrend": signal
        })

    return jsonify(out)

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
