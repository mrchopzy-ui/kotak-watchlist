from flask import Flask, render_template, jsonify, request
import csv, sqlite3, os, requests, pyotp

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

# ================= COMPANY MASTER (STRICT LOAD) =================

print("🔍 Loading NSE Company Master...")

if not os.path.exists(COMPANY_FILE):
    raise Exception(f"❌ FILE NOT FOUND: {COMPANY_FILE}")

COMPANY_MAP = {}

with open(COMPANY_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        sym = r.get("symbol", "").strip()
        name = r.get("company_name", "").strip()
        if sym and name:
            COMPANY_MAP[sym] = name

print(f"✅ Loaded {len(COMPANY_MAP)} company names")

# HARD VALIDATION
if len(COMPANY_MAP) < 1000:
    raise Exception("❌ Company master looks incomplete (<1000 rows)")

if "TCS" not in COMPANY_MAP:
    raise Exception("❌ TCS NOT FOUND in company master")

print(f"🧪 TCS → {COMPANY_MAP['TCS']}")

# ================= LOAD SCRIP MASTER =================

with open(SCRIP_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

# ================= DATABASE =================

def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS watchlists(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS stocks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER,
            trading_symbol TEXT,
            exchange_token TEXT
        )
    """)
    con.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

init_db()

# ================= KOTAK LOGIN =================

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

# ================= ROUTES =================

@app.route("/")
def index():
    con = db()
    w = con.execute("SELECT id,name FROM watchlists").fetchall()
    con.close()
    return render_template("index.html", watchlists=w)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["trading_symbol"].lower()][:10])

@app.route("/add", methods=["POST"])
def add():
    s = request.json
    con = db()
    con.execute(
        "INSERT INTO stocks(watchlist_id,trading_symbol,exchange_token) VALUES (?,?,?)",
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
        "SELECT trading_symbol,exchange_token FROM stocks WHERE watchlist_id=?",
        (wid,)
    ).fetchall()
    con.close()

    if not rows:
        return jsonify([])

    q = ",".join([f"nse_cm|{r[1]}" for r in rows])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{q}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for quote,(sym,_) in zip(data,rows):
        base = sym.replace("-EQ","")
        out.append({
            "symbol": sym,
            "company_name": COMPANY_MAP[base],
            "ltp": float(quote.get("ltp",0)),
            "pct": float(quote.get("per_change",0))
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run()
