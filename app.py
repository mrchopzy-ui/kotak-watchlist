import os
import csv
import requests
import pyotp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ======================================================
# 🔐 ENVIRONMENT VARIABLES
# ======================================================
ACCESS_TOKEN = os.environ["KOTAK_ACCESS_TOKEN"]
MOBILE = os.environ["KOTAK_MOBILE"]
USER_ID = os.environ["KOTAK_USER_ID"]
MPIN = os.environ["KOTAK_MPIN"]
TOTP_SECRET = os.environ["KOTAK_TOTP_SECRET"]

# ======================================================
# 🌐 GLOBAL STATE
# ======================================================
BASE_URL = None
SESSION_TOKEN = None
SESSION_SID = None

WATCHLISTS = {
    "Watchlist 1": [],
    "Watchlist 2": [],
    "Watchlist 3": []
}
ACTIVE_TAB = "Watchlist 1"

SCRIP_MASTER = []
INITIALIZED = False   # 🔴 IMPORTANT FLAG


# ======================================================
# 🔑 LOGIN (KOTAK v3)
# ======================================================
def login():
    global BASE_URL, SESSION_TOKEN, SESSION_SID

    totp = pyotp.TOTP(TOTP_SECRET).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi",
            "Content-Type": "application/json"
        },
        json={
            "mobileNumber": MOBILE,
            "ucc": USER_ID,
            "totp": totp
        }
    ).json()

    view_token = r1["data"]["token"]
    view_sid = r1["data"]["sid"]

    r2 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi",
            "sid": view_sid,
            "Auth": view_token,
            "Content-Type": "application/json"
        },
        json={"mpin": MPIN}
    ).json()

    BASE_URL = r2["data"]["baseUrl"]
    SESSION_TOKEN = r2["data"]["token"]
    SESSION_SID = r2["data"]["sid"]


# ======================================================
# 📂 LOAD SCRIP MASTER (NSE EQ ONLY)
# ======================================================
def load_scrip_master():
    global SCRIP_MASTER

    r = requests.get(
        f"{BASE_URL}/script-details/1.0/masterscrip/file-paths",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    nse_file = [x for x in r["data"]["filesPaths"] if "nse_cm" in x][0]
    csv_text = requests.get(nse_file).text.splitlines()

    reader = csv.DictReader(csv_text)
    for row in reader:
        if row.get("series") == "EQ":
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": row["pSymbol"],
                "trading_symbol": row["pTrdSymbol"],
                "company_name": row.get("name", row["pTrdSymbol"])
            })


# ======================================================
# 🚀 INITIALIZE APP (RUNS UNDER GUNICORN)
# ======================================================
@app.before_request
def initialize_once():
    global INITIALIZED
    if not INITIALIZED:
        print("🔐 Logging in to Kotak...")
        login()
        print("📂 Loading scrip master...")
        load_scrip_master()
        print(f"✅ Loaded {len(SCRIP_MASTER)} EQ stocks")
        INITIALIZED = True


# ======================================================
# 🔍 SEARCH (SYMBOL + COMPANY)
# ======================================================
@app.route("/search")
def search():
    q = request.args.get("q", "").lower().strip()
    if not q:
        return jsonify([])

    results = []
    for s in SCRIP_MASTER:
        if q in s["trading_symbol"].lower() or q in s["company_name"].lower():
            results.append(s)

    return jsonify(results[:10])


# ======================================================
# ➕ ADD / ❌ REMOVE
# ======================================================
@app.route("/add", methods=["POST"])
def add():
    s = request.json
    if s not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(s)
    return "", 204


@app.route("/remove", methods=["POST"])
def remove():
    key = request.json["symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if f"{s['exchange']}|{s['exchange_token']}" != key
    ]
    return "", 204


# ======================================================
# 📈 QUOTES
# ======================================================
@app.route("/prices")
def prices():
    wl = WATCHLISTS[ACTIVE_TAB]
    if not wl:
        return jsonify([])

    q = ",".join([f"{s['exchange']}|{s['exchange_token']}" for s in wl])
    url = f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}/all"

    r = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for i, d in enumerate(r):
        s = wl[i]
        ohlc = d.get("ohlc", {})
        out.append({
            **s,
            "ltp": float(d.get("ltp", 0)),
            "per_change": float(d.get("per_change", 0)),
            "last_volume": float(d.get("last_volume", 0)),
            "ohlc": {
                "open": float(ohlc.get("open", 0)),
                "high": float(ohlc.get("high", 0)),
                "low": float(ohlc.get("low", 0)),
                "close": float(ohlc.get("close", 0))
            }
        })
    return jsonify(out)


# ======================================================
# 🌐 UI
# ======================================================
@app.route("/")
def index():
    return render_template("index.html")
