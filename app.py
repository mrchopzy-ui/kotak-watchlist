from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp, json

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DATA_FILE = "data/nse_eq_scrip_master.csv"
COMPANY_FILE = "data/company_master.json"
DB_FILE = "watchlists.db"

SESSION = {}
SCRIPS = {}
COMPANY_NAMES = {}

# ---------- LOAD COMPANY MASTER ----------
with open(COMPANY_FILE, "r", encoding="utf-8") as f:
    COMPANY_NAMES = json.load(f)

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
with open(DATA_FILE, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        sym = r["trading_symbol"].replace("-EQ", "")
        SCRIPS[r["trading_symbol"]] = {
            "trading_symbol": r["trading_symbol"],
            "exchange_token": r["exchange_token"],
            "company_name": COMPANY_NAMES.get(sym, sym)
        }

# ---------- ROUTES ----------
@app.route("/")
def index():
    con = db()
    w = con.execute("SELECT id,name FROM watchlists").fetchall()
    con.close()
    return render_template("index.html", watchlists=w)

@app.route("/search")
def search():
    q = request.args.get("q", "").upper()
    return jsonify(
        [v for k, v in SCRIPS.items() if q in k][:10]
    )

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    con = db()
    con.execute(
        "INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token) VALUES (?,?,?)",
        (request.args.get("wid"), s["trading_symbol"], s["exchange_token"])
    )
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    con = db()
    rows = con.execute(
        "SELECT trading_symbol, exchange_token FROM stocks WHERE watchlist_id=?",
        (wid,)
    ).fetchall()
    con.close()

    if not rows:
        return jsonify([])

    q = ",".join([f"nse_cm|{r[1]}" for r in rows])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{q}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for quote, r in zip(data, rows):
        sym = r[0].replace("-EQ", "")
        out.append({
            "symbol": r[0],
            "company_name": COMPANY_NAMES.get(sym, sym),
            "ltp": float(quote.get("ltp", 0)),
            "pct": float(quote.get("per_change", 0))
        })
    return jsonify(out)
