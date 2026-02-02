from flask import Flask, render_template, jsonify, request
import csv, os, requests, pyotp

app = Flask(__name__)

# ---------- ENV VARIABLES ----------
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

# ---------- LOGIN ----------
def login():
    totp = pyotp.TOTP(TOTP_SECRET).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={"Authorization": ACCESS_TOKEN, "neo-fin-key": "neotradeapi"},
        json={"mobileNumber": MOBILE, "ucc": USER_ID, "totp": totp}
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

# ---------- LOAD SCRIP MASTER ----------
with open(DATA_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

# ---------- HELPERS ----------
def fmt_vol(v):
    v = float(v)
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.2f}K"
    return str(int(v))

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", tabs=WATCHLISTS.keys(), active=ACTIVE_TAB)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["trading_symbol"].lower()][:10])

@app.route("/add", methods=["POST"])
def add():
    s = request.json
    if s not in WATCHLISTS[ACTIVE_TAB]:
        WATCHLISTS[ACTIVE_TAB].append(s)
    return "", 204

@app.route("/remove", methods=["POST"])
def remove():
    sym = request.json["trading_symbol"]
    WATCHLISTS[ACTIVE_TAB] = [s for s in WATCHLISTS[ACTIVE_TAB] if s["trading_symbol"] != sym]
    return "", 204

@app.route("/prices")
def prices():
    if not WATCHLISTS[ACTIVE_TAB]:
        return jsonify([])

    q = ",".join(f"nse_cm|{s['exchange_token']}" for s in WATCHLISTS[ACTIVE_TAB])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{q}/all"

    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()
    out = []

    for r, s in zip(data, WATCHLISTS[ACTIVE_TAB]):
        o = r.get("ohlc", {})
        out.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "ltp": float(r["ltp"]),
            "change_pct": float(r["per_change"]),
            "open": float(o.get("open", 0)),
            "high": float(o.get("high", 0)),
            "low": float(o.get("low", 0)),
            "close": float(o.get("close", 0)),
            "volume": fmt_vol(r.get("last_volume", 0))
        })

    return jsonify(out)

@app.route("/new-tab", methods=["POST"])
def new_tab():
    WATCHLISTS[request.json["name"]] = []
    return "", 204

@app.route("/set-tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return "", 204

if __name__ == "__main__":
    app.run()
