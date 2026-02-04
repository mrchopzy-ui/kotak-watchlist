from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

SCRIP_FILE = "data/nse_eq_scrip_master.csv"
COMPANY_FILE = "data/nse_company_master.csv"
DB_FILE = "watchlists.db"

SESSION = {}
SCRIPS = []
COMPANIES = {}

# -------------------- DB --------------------

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

# -------------------- LOGIN --------------------

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

# -------------------- LOAD MASTERS --------------------

with open(SCRIP_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

with open(COMPANY_FILE, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        COMPANIES[r["symbol"].strip()] = r["company_name"].strip()

# -------------------- HELPERS --------------------

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

def nse_symbol(trading_symbol):
    # TCS-EQ -> TCS
    return trading_symbol.split("-")[0]

# -------------------- ROUTES --------------------

@app.route("/")
def index():
    return render_template("index.html", watchlists=get_watchlists())

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["trading_symbol"].lower()][:10])

@app.route("/watchlist", methods=["POST"])
def create_watchlist():
    con = db()
    con.execute("INSERT INTO watchlists(name) VALUES (?)", (request.json["name"],))
    con.commit()
    con.close()
    return "", 204

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    con = db()
    con.execute("UPDATE watchlists SET name=? WHERE id=?", (request.json["name"], wid))
    con.commit()
    con.close()
    return "", 204

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    con = db()
    con.execute("""
        INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token)
        VALUES (?, ?, ?)
    """, (request.args.get("wid"), s["trading_symbol"], s["exchange_token"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    con = db()
    con.execute(
        "DELETE FROM stocks WHERE watchlist_id=? AND trading_symbol=?",
        (request.args.get("wid"), request.json["trading_symbol"])
    )
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
        sym = nse_symbol(s[0])  # FIX IS HERE
        o = q.get("ohlc", {})

        out.append({
            "symbol": s[0],
            "company_name": COMPANIES.get(sym, sym),
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0)),
            "volume": format_volume(q.get("last_volume", 0)),
            "open": o.get("open", 0),
            "high": o.get("high", 0),
            "low": o.get("low", 0),
            "close": o.get("close", 0)
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run()
