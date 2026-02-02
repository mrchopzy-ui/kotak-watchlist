from flask import Flask, render_template, jsonify, request
import csv
import os
import requests
import pyotp

app = Flask(__name__)

# ---------------- CONFIG (ENV VARIABLES) ----------------

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

# ---------------- LOGIN ----------------

def login():
    print("🔐 Logging in to Kotak...")
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
    SESSION["sid"] = r2["data"]["sid"]
    SESSION["token"] = r2["data"]["token"]

login()

# ---------------- LOAD SCRIP MASTER ----------------

def load_scrip_master():
    global SCRIPS
    print("📂 Loading LOCAL scrip master...")

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        SCRIPS = list(csv.DictReader(f))

    if not SCRIPS:
        raise SystemExit("❌ Local scrip master is empty")

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
    sym = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        s for s in WATCHLISTS[ACTIVE_TAB]
        if s["trading_symbol"] != sym
    ]
    return "", 204

# ---------------- LIVE PRICES ----------------

@app.route("/prices")
def prices():
    if not WATCHLISTS[ACTIVE_TAB]:
        return jsonify([])

    queries = ",".join(
        f"nse_cm|{s['exchange_token']}"
        for s in WATCHLISTS[ACTIVE_TAB]
    )

    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"

    r = requests.get(
        url,
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out = []
    for q, s in zip(r, WATCHLISTS[ACTIVE_TAB]):
        ohlc = q.get("ohlc", {})

        out.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "ltp": float(q["ltp"]),
            "change_pct": float(q["per_change"]),
            "open": float(ohlc.get("open", 0)),
            "high": float(ohlc.get("high", 0)),
            "low": float(ohlc.get("low", 0)),
            "close": float(ohlc.get("close", 0))
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
