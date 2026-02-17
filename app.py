import os, csv, sqlite3, requests, pyotp
from flask import Flask, request, jsonify, render_template

# ========== ENV ==========
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DB = "watchlist.db"
BASE_URL = None

app = Flask(__name__)

# ========== DB ==========
def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    c = db()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS watchlists(id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("""CREATE TABLE IF NOT EXISTS instruments(
        watchlist_id INTEGER,
        exchange_segment TEXT,
        exchange_token TEXT,
        trading_symbol TEXT
    )""")
    if cur.execute("SELECT COUNT(*) FROM watchlists").fetchone()[0] == 0:
        cur.execute("INSERT INTO watchlists(name) VALUES('Watchlist 1')")
    c.commit()
    c.close()

# ========== LOGIN ==========
def kotak_login():
    global BASE_URL
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

    BASE_URL = r2["data"]["baseUrl"]

# ========== LOAD SCRIP MASTERS ==========
SEARCH_POOL = []

def load_scrips():
    global SEARCH_POOL
    SEARCH_POOL = []

    # EQ
    with open("nse_eq_scrip_master.csv", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            SEARCH_POOL.append({
                "exchange_segment": "nse_cm",
                "exchange_token": r["pSymbol"],
                "trading_symbol": r["pTrdSymbol"],
                "search_key": r["pTrdSymbol"].lower()
            })

    # F&O
    with open("nse_fo_scrip_master.csv", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            sym = r["tradingSymbol"]
            SEARCH_POOL.append({
                "exchange_segment": "nse_fo",
                "exchange_token": r["exchangeToken"],
                "trading_symbol": sym,
                "search_key": sym.lower()
            })

# ========== ROUTES ==========
@app.route("/")
def index():
    w = db().execute("SELECT id,name FROM watchlists").fetchall()
    return render_template("index.html", watchlists=w)

@app.route("/search")
def search():
    q = request.args.get("q","").lower()
    res = [s for s in SEARCH_POOL if q in s["search_key"]][:20]
    return jsonify(res)

@app.route("/add", methods=["POST"])
def add():
    d = request.json
    db().execute(
        "INSERT INTO instruments VALUES(?,?,?,?)",
        (request.args["wid"], d["exchange_segment"], d["exchange_token"], d["trading_symbol"])
    ).connection.commit()
    return "",204

@app.route("/remove", methods=["POST"])
def remove():
    d = request.json
    db().execute(
        "DELETE FROM instruments WHERE watchlist_id=? AND exchange_segment=? AND exchange_token=?",
        (request.args["wid"], d["exchange_segment"], d["exchange_token"])
    ).connection.commit()
    return "",204

@app.route("/prices")
def prices():
    rows = db().execute(
        "SELECT exchange_segment,exchange_token,trading_symbol FROM instruments WHERE watchlist_id=?",
        (request.args["wid"],)
    ).fetchall()

    if not rows:
        return jsonify([])

    q = ",".join([f"{r[0]}|{r[1]}" for r in rows])

    r = requests.get(
        f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}/all",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out = []
    for i,x in enumerate(r):
        out.append({
            "symbol": rows[i][2],
            "company": x.get("instrumentName", rows[i][2]),
            "ltp": float(x["ltp"]),
            "pct": float(x["per_change"]),
            "volume": x.get("last_volume","-"),
            "open": x["ohlc"]["open"],
            "high": x["ohlc"]["high"],
            "low": x["ohlc"]["low"],
            "close": x["ohlc"]["close"],
            "exchange_segment": rows[i][0],
            "exchange_token": rows[i][1]
        })
    return jsonify(out)

# ========== BOOT ==========
init_db()
kotak_login()
load_scrips()

if __name__ == "__main__":
    app.run()
