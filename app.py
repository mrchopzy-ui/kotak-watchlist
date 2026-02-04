from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

SCRIP_FILE = "data/nse_eq_scrip_master.csv"
DB_FILE = "watchlists.db"

SESSION = {}
SCRIPS = []

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
            exchange_token TEXT,
            company_name TEXT
        )
    """)

    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

init_db()

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

with open(SCRIP_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

def get_company_name_from_nse(symbol):
    sym = symbol.replace("-EQ", "")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nseindia.com"
    })

    session.get("https://www.nseindia.com", timeout=10)
    r = session.get(
        f"https://www.nseindia.com/api/quote-equity?symbol={sym}",
        timeout=10
    )

    if r.status_code != 200:
        return sym

    return r.json().get("info", {}).get("companyName", sym)

def get_watchlists():
    con = db()
    rows = con.execute("SELECT id, name FROM watchlists ORDER BY id").fetchall()
    con.close()
    return rows

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

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    wid = request.args.get("wid")

    company = get_company_name_from_nse(s["trading_symbol"])

    con = db()
    con.execute("""
        INSERT INTO stocks
        (watchlist_id, trading_symbol, exchange_token, company_name)
        VALUES (?, ?, ?, ?)
    """, (wid, s["trading_symbol"], s["exchange_token"], company))
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    con = db()
    stocks = con.execute("""
        SELECT trading_symbol, exchange_token, company_name
        FROM stocks WHERE watchlist_id=?
    """, (wid,)).fetchall()
    con.close()

    if not stocks:
        return jsonify([])

    queries = ",".join([f"nse_cm|{s[1]}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q, s in zip(data, stocks):
        out.append({
            "symbol": s[0],
            "company_name": s[2],
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0))
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run()
