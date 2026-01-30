from flask import Flask, render_template, jsonify, request
import requests
import pyotp
import time

app = Flask(__name__)

# =======================
# USER CONFIG (EDIT ONLY THIS)
# =======================
ACCESS_TOKEN = "5299a2a1-21fa-42e2-b9b3-b63be76a2553"
MOBILE_NUMBER = "+919551441970"
USER_ID = "YALD5"
MPIN = "124689"
TOTP_SECRET = "YOYAZGFRWAU2FXZM2XA43RVQVU"

# =======================
# GLOBAL SESSION DATA
# =======================
BASE_URL = ""
AUTH = ""
SID = ""

watchlist = ["nse_cm|6863"]
candles = {}   # {symbol: [ {x,o,h,l,c} ]}

# =======================
# LOGIN
# =======================
def kotak_login():
    global BASE_URL, AUTH, SID

    print("Logging into Kotak...")
    totp = pyotp.TOTP(TOTP_SECRET).now()
    print("Generated TOTP:", totp)

    login = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi",
            "Content-Type": "application/json"
        },
        json={
            "mobileNumber": MOBILE,
            "ucc": UCC,
            "totp": totp
        }
    ).json()

    view_token = login["data"]["token"]
    view_sid = login["data"]["sid"]

    validate = requests.post(
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

    BASE_URL = validate["data"]["baseUrl"]
    AUTH = validate["data"]["token"]
    SID = validate["data"]["sid"]

    print("✅ LOGIN SUCCESSFUL")
    print("Base URL:", BASE_URL)

# =======================
# ROUTES
# =======================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chart")
def chart():
    return render_template("chart.html")

@app.route("/watchlist")
def get_watchlist():
    return jsonify(watchlist)

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json["symbol"]
    if s not in watchlist:
        watchlist.append(s)
    return jsonify({"ok": True})

@app.route("/prices")
def prices():
    now = int(time.time() * 1000)

    for s in watchlist:
        # Fake price for now (safe & stable)
        price = round(100 + time.time() % 10, 2)

        candles.setdefault(s, []).append({
            "x": now,
            "o": price - 1,
            "h": price + 1,
            "l": price - 2,
            "c": price
        })

        candles[s] = candles[s][-100:]  # keep last 100 candles

    return jsonify({"ok": True})

@app.route("/candles/<path:symbol>")
def get_candles(symbol):
    return jsonify(candles.get(symbol, []))

# =======================
# START
# =======================
if __name__ == "__main__":
    kotak_login()
    app.run(debug=True)
