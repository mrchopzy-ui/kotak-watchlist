from flask import Flask, render_template, jsonify, request
import csv
import os
import requests
import pyotp

app = Flask(__name__)

# -------- ENV VARIABLES --------
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DATA_FILE = "data/nse_eq_scrip_master.csv"

WATCHLISTS = {"Watchlist 1": []}
ACTIVE_TAB = "Watchlist 1"
SCRIPS = []
SESSION = {}

# -------- INDICES (STATIC) --------
INDICES = [
    {
        "type": "INDEX",
        "symbol": "NIFTY 50",
        "company_name": "NIFTY 50",
        "exchange_token": "Nifty 50"
    },
    {
        "type": "INDEX",
        "symbol": "NIFTY BANK",
        "company_name": "NIFTY BANK",
        "exchange_token": "Nifty Bank"
    }
]

# -------- LOGIN --------
def login():
    totp = pyotp.TOTP(TOTP_SECRET).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi"
        },
        json={
            "mobileNumber": MOBILE,
            "ucc": USER_ID,
            "totp": totp
        }
    ).json()

    r2 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi",
            "sid": r1["data"]["sid"],
            "Auth": r1["data"]["token"]
        },
        json={"mpin": MPIN}
    ).json()

    SESSION["base"] = r2["data"]["baseUrl"]

login()

# -------- LOAD SCRIP MASTER --------
def load_scrip_master():
    global SCRIPS
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        SCRIPS = list(csv.DictReader(f))

    if not SCRIPS:
        raise SystemExit("❌ Local scrip master empty")

load_scrip_master()

# -------- ROUTES --------
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
        s for s in SCRIPS if q in s["trading_symbol"].lower()
    ][:10])

@app.route("/add", methods=["POST"])
def add_stock():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    sym = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != sym
    ]
    return "", 204

# -------- PRICES (STOCKS + INDICES) --------
@app.route("/prices")
def prices():
    items = INDICES + WATCHLISTS[ACTIVE_TAB]

    queries = []
    for i in items:
        if i.get("type") == "INDEX":
            queries.append(f"nse_cm|{i['exchange_token']}")
        else:
            queries.append(f"nse_cm|{i['exchange_token']}")

    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{','.join(queries)}/all"

    resp = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q, i in zip(resp, items):
        ohlc = q.get("ohlc", {})

        out.append({
            "symbol": i["symbol"] if i.get("type") == "INDEX" else i["trading_symbol"],
            "company": i["company_name"],
            "ltp": float(q.get("ltp", 0)),
            "change_pct": float(q.get("per_change", 0)),
            "volume": int(q.get("last_volume", 0)),
            "open": float(ohlc.get("open", 0)),
            "high": float(ohlc.get("high", 0)),
            "low": float(ohlc.get("low", 0)),
            "close": float(ohlc.get("close", 0)),
            "is_index": i.get("type") == "INDEX"
        })

    return jsonify(out)

@app.route("/new-tab", methods=["POST"])
def new_tab():
    name = request.json["name"]
    WATCHLISTS[name] = []
    return "", 204

@app.route("/set-tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return "", 204

if __name__ == "__main__":
    app.run()
