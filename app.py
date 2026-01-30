import os
import csv
import requests
import pyotp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ======================================================
# 🔐 ENVIRONMENT VARIABLES
# ======================================================
ACCESS_TOKEN = os.environ.get("KOTAK_ACCESS_TOKEN")
MOBILE = os.environ.get("KOTAK_MOBILE")
USER_ID = os.environ.get("KOTAK_USER_ID")
MPIN = os.environ.get("KOTAK_MPIN")
TOTP_SECRET = os.environ.get("KOTAK_TOTP_SECRET")

if not all([ACCESS_TOKEN, MOBILE, USER_ID, MPIN, TOTP_SECRET]):
    raise RuntimeError("❌ Missing Kotak environment variables")

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

# ======================================================
# 🔑 LOGIN
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
        json={"mobileNumber": MOBILE, "ucc": USER_ID, "totp": totp},
        timeout=10
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
        json={"mpin": MPIN},
        timeout=10
    ).json()

    BASE_URL = r2["data"]["baseUrl"]
    SESSION_TOKEN = r2["data"]["token"]
    SESSION_SID = r2["data"]["sid"]

# ======================================================
# 📂 LOAD LOCAL SCRIP MASTER
# ======================================================
def load_local_scrip_master():
    global SCRIP_MASTER
    path = os.path.join("data", "nse_eq_scrip_master.csv")

    if not os.path.exists(path):
        raise RuntimeError("❌ nse_eq_scrip_master.csv not found")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            SCRIP_MASTER.append({
                "exchange": "nse_cm",
                "exchange_token": r["exchange_token"],
                "trading_symbol": r["trading_symbol"],
                "company_name": r["company_name"]
            })

    if not SCRIP_MASTER:
        raise RuntimeError("❌ Local scrip master is empty")

# ======================================================
# 🚀 INIT
# ======================================================
print("🔐 Logging in to Kotak...")
login()

print("📂 Loading LOCAL scrip master...")
load_local_scrip_master()

print(f"✅ Loaded {len(SCRIP_MASTER)} stocks")

# ======================================================
# 🔍 SEARCH
# ======================================================
@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([
        s for s in SCRIP_MASTER
        if q in s["trading_symbol"].lower()
    ][:10])

# ======================================================
# ➕ ADD
# ======================================================
@app.route("/add", methods=["POST"])
def add():
    stock = request.json
    if stock not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(stock)
    return "", 204

# ======================================================
# 📈 PRICES
# ======================================================
@app.route("/prices")
def prices():
    return jsonify(WATCHLISTS[ACTIVE_TAB])

# ======================================================
# 🌐 UI
# ======================================================
@app.route("/")
def index():
    return render_template("index.html")

# ======================================================
# 🟢 PORT BINDING (CRITICAL FOR RENDER)
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
