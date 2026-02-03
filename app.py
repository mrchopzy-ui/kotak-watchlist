from flask import Flask, render_template, jsonify, request
import requests
import pyotp
import csv
import io

app = Flask(__name__)

# ==============================
# 🔐 USER CONFIG (EDIT ONLY THIS)
# ==============================
ACCESS_TOKEN = "PASTE_YOUR_ACCESS_TOKEN"
MOBILE_NUMBER = "+91XXXXXXXXXX"
USER_ID = "YOUR_UCC"
MPIN = "123456"
TOTP_SECRET = "PASTE_TOTP_SECRET"

# ==============================
BASE_URL = None
SESSION_TOKEN = None
SESSION_SID = None

WATCHLIST = []
SCRIPS = []   # autocomplete list

# ==============================
# LOGIN
# ==============================
def kotak_login():
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
            "mobileNumber": MOBILE_NUMBER,
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
            "Auth": r1["data"]["token"],
            "Content-Type": "application/json"
        },
        json={"mpin": MPIN}
    ).json()

    BASE_URL = r2["data"]["baseUrl"]
    SESSION_TOKEN = r2["data"]["token"]
    SESSION_SID = r2["data"]["sid"]

# ==============================
# LOAD SCRIP MASTER (NSE CM)
# ==============================
def load_scrip_master():
    global SCRIPS

    r = requests.get(
        f"{BASE_URL}/script-details/1.0/masterscrip/file-paths",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    # pick NSE cash file
    nse_cm_file = [f for f in r["data"]["filesPaths"] if "nse_cm" in f][0]
    csv_text = requests.get(nse_cm_file).text

    reader = csv.DictReader(io.StringIO(csv_text))

    for row in reader:
        if row.get("pTrdSymbol") and row.get("pSymbol"):
            SCRIPS.append({
                "name": row["pTrdSymbol"],          # company / trading name
                "symbol": f"nse_cm|{row['pSymbol']}"
            })

# ==============================
# QUOTES
# ==============================
def get_quotes():
    if not WATCHLIST:
        return []

    q = ",".join(WATCHLIST)
    url = f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}/all"

    return requests.get(
        url,
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

# ==============================
# ROUTES
# ==============================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    results = [s for s in SCRIPS if q in s["name"].lower()][:8]
    return jsonify(results)

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json["symbol"]
    if s not in WATCHLIST and len(WATCHLIST) < 10:
        WATCHLIST.append(s)
    return jsonify({"ok": True})

@app.route("/remove", methods=["POST"])
def remove_stock():
    s = request.json["symbol"]
    if s in WATCHLIST:
        WATCHLIST.remove(s)
    return jsonify({"ok": True})

@app.route("/prices")
def prices():
    return jsonify(get_quotes())

# ==============================
if __name__ == "__main__":
    print("Logging in...")
    kotak_login()
    print("Loading scrip master...")
    load_scrip_master()
    print("Ready.")
    app.run(debug=True)
