from flask import Flask, render_template, jsonify, request
import requests, pyotp, csv, io, json, os

app = Flask(__name__)

# ================= USER CONFIG =================
ACCESS_TOKEN = "5299a2a1-21fa-42e2-b9b3-b63be76a2553"
MOBILE_NUMBER = "+919551441970"
USER_ID = "YALD5"
MPIN = "124689"
TOTP_SECRET = "YOYAZGFRWAU2FXZM2XA43RVQVU"
# ==============================================

WATCHLIST_FILE = "watchlist.json"

BASE_URL = None
SESSION_TOKEN = None
SESSION_SID = None

WATCHLISTS = {}          # { tab_name: [stocks] }
TAB_ORDER = []           # ["Watchlist 1", "Watchlist 2", ...]
ACTIVE_TAB = None

SCRIPS = []
NSE_NAMES = {}

# ================= WATCHLIST LOAD/SAVE =================
def load_watchlists():
    global WATCHLISTS, TAB_ORDER, ACTIVE_TAB

    if not os.path.exists(WATCHLIST_FILE):
        WATCHLISTS = {
            "Watchlist 1": [],
            "Watchlist 2": [],
            "Watchlist 3": []
        }
        TAB_ORDER = list(WATCHLISTS.keys())
        ACTIVE_TAB = TAB_ORDER[0]
        save_watchlists()
        return

    with open(WATCHLIST_FILE, "r") as f:
        data = json.load(f)

    # 🔁 Migration support
    if isinstance(data, list):
        WATCHLISTS = {
            "Watchlist 1": data,
            "Watchlist 2": [],
            "Watchlist 3": []
        }
        TAB_ORDER = list(WATCHLISTS.keys())
    else:
        WATCHLISTS = data.get("watchlists", data)
        TAB_ORDER = data.get("tab_order", list(WATCHLISTS.keys()))

    ACTIVE_TAB = TAB_ORDER[0]

def save_watchlists():
    with open(WATCHLIST_FILE, "w") as f:
        json.dump({
            "watchlists": WATCHLISTS,
            "tab_order": TAB_ORDER
        }, f, indent=2)

# ================= LOGIN =================
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
        json={"mobileNumber": MOBILE_NUMBER, "ucc": USER_ID, "totp": totp}
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

# ================= NSE COMPANY NAMES =================
def load_nse_company_names():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    csv_text = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    reader = csv.DictReader(io.StringIO(csv_text))
    for r in reader:
        NSE_NAMES[r["SYMBOL"]] = r["NAME OF COMPANY"].title()

# ================= EQ SCRIP MASTER =================
def load_scrip_master():
    r = requests.get(
        f"{BASE_URL}/script-details/1.0/masterscrip/file-paths",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    file = [f for f in r["data"]["filesPaths"] if "nse_cm" in f][0]
    csv_text = requests.get(file).text
    reader = csv.DictReader(io.StringIO(csv_text))

    for row in reader:
        token = row.get("pSymbol")
        trd = row.get("pTrdSymbol")
        if not token or not trd or not trd.endswith("-EQ"):
            continue

        base = trd.replace("-EQ", "")
        SCRIPS.append({
            "symbol": f"nse_cm|{token}",
            "trading_symbol": trd,
            "company_name": NSE_NAMES.get(base, trd)
        })

# ================= QUOTES =================
def get_quotes(tab):
    wl = WATCHLISTS.get(tab, [])
    if not wl:
        return []

    symbols = ",".join(w["symbol"] for w in wl)
    url = f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{symbols}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q in data:
        key = f"{q['exchange']}|{q['exchange_token']}"
        meta = next(w for w in wl if w["symbol"] == key)
        q["company_name"] = meta["company_name"]
        q["trading_symbol"] = meta["trading_symbol"]
        out.append(q)
    return out

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html", tabs=TAB_ORDER)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["company_name"].lower()][:8])

@app.route("/set_tab", methods=["POST"])
def set_tab():
    global ACTIVE_TAB
    ACTIVE_TAB = request.json["tab"]
    return jsonify({"ok": True})

@app.route("/reorder_tabs", methods=["POST"])
def reorder_tabs():
    global TAB_ORDER
    TAB_ORDER = request.json["order"]
    save_watchlists()
    return jsonify({"ok": True})

@app.route("/rename_tab", methods=["POST"])
def rename_tab():
    global ACTIVE_TAB
    old = request.json["old"]
    new = request.json["new"].strip()
    if not new or new in WATCHLISTS:
        return jsonify({"ok": False})

    WATCHLISTS[new] = WATCHLISTS.pop(old)
    TAB_ORDER[TAB_ORDER.index(old)] = new
    if ACTIVE_TAB == old:
        ACTIVE_TAB = new
    save_watchlists()
    return jsonify({"ok": True})

@app.route("/add", methods=["POST"])
def add():
    if len(WATCHLISTS[ACTIVE_TAB]) < 10:
        if request.json not in WATCHLISTS[ACTIVE_TAB]:
            WATCHLISTS[ACTIVE_TAB].append(request.json)
            save_watchlists()
    return jsonify({"ok": True})

@app.route("/remove", methods=["POST"])
def remove():
    sym = request.json["symbol"]
    WATCHLISTS[ACTIVE_TAB] = [
        w for w in WATCHLISTS[ACTIVE_TAB] if w["symbol"] != sym
    ]
    save_watchlists()
    return jsonify({"ok": True})

@app.route("/prices")
def prices():
    return jsonify(get_quotes(ACTIVE_TAB))

# ================= START =================
if __name__ == "__main__":
    kotak_login()
    load_nse_company_names()
    load_scrip_master()
    load_watchlists()
    app.run(debug=True)
