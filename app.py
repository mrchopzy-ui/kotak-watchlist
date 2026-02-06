from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp

app = Flask(__name__)

# ---------- ENV ----------
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DB_FILE = "watchlists.db"
SCRIP_FILE = "data/nse_eq_scrip_master.csv"
EQUITY_FILE = "data/EQUITY_L.csv"
MCAP_FILE = "data/mcap05022026.csv"

SESSION = {}
SCRIPS = []
COMPANY_MAP = {}
SEARCH_LIST = []

# ---------- DB ----------
def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlists(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER,
            trading_symbol TEXT,
            exchange_token TEXT
        )
    """)
    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

init_db()

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
with open(SCRIP_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

# ---------- MAP TOKEN BY SYMBOL ----------
TOKEN_MAP = {
    r["trading_symbol"]: r["exchange_token"]
    for r in SCRIPS
}

# ---------- LOAD COMPANY NAMES ----------
with open(EQUITY_FILE, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        sym = (r.get("SYMBOL") or "").strip().upper()
        name = (r.get("NAME") or "").strip()
        if sym and name:
            COMPANY_MAP[sym] = name

# ---------- LOAD SEARCH DATA (MCAP FILE) ----------
with open(MCAP_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        sym = (r.get("SYMBOL") or r.get("Symbol") or "").strip().upper()
        name = (r.get("COMPANY NAME") or r.get("Company") or r.get("NAME") or "").strip()
        if sym and name:
            SEARCH_LIST.append({
                "symbol": f"{sym}-EQ",
                "company": name,
                "exchange_token": TOKEN_MAP.get(f"{sym}-EQ")
            })

# ---------- HELPERS ----------
def get_watchlists():
    con = db()
    rows = con.execute("SELECT id, name FROM watchlists ORDER BY id").fetchall()
    con.close()
    return rows

def format_volume(v):
    v = float(v)
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.2f}K"
    return str(int(v))

def get_company_name(sym):
    return COMPANY_MAP.get(sym.replace("-EQ",""), sym.replace("-EQ",""))

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", watchlists=get_watchlists())

@app.route("/search")
def search():
    q = request.args.get("q","").lower()
    if not q:
        return jsonify([])

    results = [
        s for s in SEARCH_LIST
        if q in s["symbol"].lower() or q in s["company"].lower()
    ][:10]

    return jsonify(results)

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    wid = request.args.get("wid")

    if not s.get("exchange_token"):
        return "", 400

    con = db()
    con.execute("""
        INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token)
        VALUES (?, ?, ?)
    """, (wid, s["symbol"], s["exchange_token"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    con = db()
    stocks = con.execute(
        "SELECT trading_symbol, exchange_token FROM stocks WHERE watchlist_id=?",
        (wid,)
    ).fetchall()
    con.close()

    if not stocks:
        return jsonify([])

    queries = ",".join([f"nse_cm|{s[1]}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q, s in zip(data, stocks):
        o = q.get("ohlc", {})
        out.append({
            "symbol": s[0],
            "company_name": get_company_name(s[0]),
            "ltp": float(q.get("ltp",0)),
            "pct": float(q.get("per_change",0)),
            "volume": format_volume(q.get("last_volume",0)),
            "open": o.get("open",0),
            "high": o.get("high",0),
            "low": o.get("low",0),
            "close": o.get("close",0)
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run()
