import os, time, sqlite3, requests, pyotp, csv
from flask import Flask, render_template, request, jsonify
from collections import defaultdict

# ================= CONFIG =================
ACCESS_TOKEN = os.environ.get("KOTAK_ACCESS_TOKEN")
MOBILE = os.environ.get("KOTAK_MOBILE")
USER_ID = os.environ.get("KOTAK_USER_ID")
MPIN = os.environ.get("KOTAK_MPIN")
TOTP_SECRET = os.environ.get("KOTAK_TOTP_SECRET")

DB_FILE = "watchlists.db"
app = Flask(__name__)

# ================= DB =================
def db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    c = db().cursor()
    c.execute("CREATE TABLE IF NOT EXISTS watchlists(id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY,
            watchlist_id INTEGER,
            symbol TEXT,
            exchange TEXT,
            instrument_type TEXT,
            expiry TEXT,
            strike REAL,
            option_type TEXT
        )
    """)
    db().commit()

init_db()

# ================= LOGIN =================
SESSION = {}

def login():
    if SESSION.get("exp", 0) > time.time():
        return

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

    SESSION.update({
        "base": r2["data"]["baseUrl"],
        "exp": time.time() + 300
    })

# ================= EQ SEARCH (RESTORED) =================
SCRIPS = []

def load_eq_scrips():
    global SCRIPS
    try:
        with open("nse_eq_scrip_master.csv", encoding="latin-1") as f:
            SCRIPS = list(csv.DictReader(f))
    except:
        SCRIPS = []

load_eq_scrips()

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    res = [
        {"trading_symbol": r["trading_symbol"]}
        for r in SCRIPS
        if q in r["trading_symbol"].lower()
    ][:20]
    return jsonify(res)

# ================= F&O MASTER =================
FO = defaultdict(lambda: {
    "expiries": set(),
    "options": defaultdict(set)
})

def load_fo():
    try:
        login()
        p = requests.get(
            f"{SESSION['base']}/script-details/1.0/masterscrip/file-paths",
            headers={"Authorization": ACCESS_TOKEN}
        ).json()

        url = [x for x in p["data"]["filesPaths"] if "nse_fo" in x][0]
        rows = csv.DictReader(requests.get(url).text.splitlines())

        for r in rows:
            u = r.get("underlying")
            e = r.get("expiryDate")
            o = r.get("optionType")
            s = r.get("strikePrice")

            if not u or not e:
                continue

            FO[u]["expiries"].add(e)
            if o in ("CE", "PE"):
                FO[u]["options"][e].add(float(s))

    except Exception as e:
        print("FO load failed:", e)

load_fo()

@app.route("/fo/underlyings")
def fo_underlyings():
    return jsonify(sorted(FO.keys()))

@app.route("/fo/expiries")
def fo_expiries():
    return jsonify(sorted(FO.get(request.args["u"], {}).get("expiries", [])))

@app.route("/fo/strikes")
def fo_strikes():
    return jsonify(sorted(
        FO.get(request.args["u"], {}).get("options", {}).get(request.args["e"], [])
    ))

# ================= QUOTES =================
def quotes(rows):
    login()
    if not rows:
        return []
    syms = ",".join(f"{r['exchange']}|{r['symbol']}" for r in rows)
    r = requests.get(
        f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{syms}/all",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out = []
    for q in r:
        out.append({
            "symbol": q.get("display_symbol"),
            "company": q.get("instrument_name") or q.get("display_symbol"),
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0)),
            "volume": q.get("last_volume", 0),
            "open": q.get("ohlc", {}).get("open", 0),
            "high": q.get("ohlc", {}).get("high", 0),
            "low": q.get("ohlc", {}).get("low", 0),
            "close": q.get("ohlc", {}).get("close", 0),
        })
    return out

# ================= ROUTES =================
@app.route("/")
def home():
    w = db().execute("SELECT id,name FROM watchlists").fetchall()
    if not w:
        db().execute("INSERT INTO watchlists(name) VALUES('Watchlist 1')")
        db().commit()
        w = db().execute("SELECT id,name FROM watchlists").fetchall()
    return render_template("index.html", watchlists=w)

@app.route("/prices")
def prices():
    rows = db().execute(
        "SELECT symbol,exchange,instrument_type,expiry,strike,option_type FROM items WHERE watchlist_id=?",
        (request.args["wid"],)
    ).fetchall()

    data = [{"symbol":r[0],"exchange":r[1]} for r in rows]
    return jsonify(quotes(data))

@app.route("/add", methods=["POST"])
def add():
    d = request.json
    db().execute(
        "INSERT INTO items(watchlist_id,symbol,exchange,instrument_type,expiry,strike,option_type) VALUES (?,?,?,?,?,?,?)",
        (request.args["wid"], d["symbol"], d["exchange"], d["instrument_type"], d.get("expiry"), d.get("strike"), d.get("option_type"))
    )
    db().commit()
    return "",204

@app.route("/remove", methods=["POST"])
def remove():
    db().execute(
        "DELETE FROM items WHERE watchlist_id=? AND symbol=?",
        (request.args["wid"], request.json["trading_symbol"])
    )
    db().commit()
    return "",204

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
