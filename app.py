from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp

app = Flask(__name__)

# ---------------- ENV ----------------
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DATA_FILE = "data/nse_eq_scrip_master.csv"
DB_FILE = "watchlists.db"

SESSION = {}
SCRIPS = []

# ---------------- DB ----------------
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
            company_name TEXT,
            exchange_token TEXT
        )
    """)
    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

init_db()

# ---------------- LOGIN ----------------
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

# ---------------- LOAD SCRIP MASTER ----------------
with open(DATA_FILE, newline="", encoding="utf-8") as f:
    SCRIPS = list(csv.DictReader(f))

# ---------------- HELPERS ----------------
def get_watchlists():
    con = db()
    rows = con.execute("SELECT id, name FROM watchlists ORDER BY id").fetchall()
    con.close()
    return rows

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", watchlists=get_watchlists())

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["trading_symbol"].lower()][:10])

@app.route("/watchlist", methods=["POST"])
def create_watchlist():
    name = request.json.get("name")
    if not name:
        return "", 400

    con = db()
    con.execute("INSERT INTO watchlists(name) VALUES (?)", (name,))
    con.commit()
    con.close()
    return "", 204

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    name = request.json.get("name")
    if not name:
        return "", 400

    con = db()
    con.execute("UPDATE watchlists SET name=? WHERE id=?", (name, wid))
    con.commit()
    con.close()
    return "", 204

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    wid = request.args.get("wid")

    con = db()
    con.execute("""
        INSERT INTO stocks (watchlist_id, trading_symbol, company_name, exchange_token)
        VALUES (?, ?, ?, ?)
    """, (wid, s["trading_symbol"], s["company_name"], s["exchange_token"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    sym = request.json["trading_symbol"]
    wid = request.args.get("wid")

    con = db()
    con.execute(
        "DELETE FROM stocks WHERE watchlist_id=? AND trading_symbol=?",
        (wid, sym)
    )
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")

    con = db()
    stocks = con.execute(
        "SELECT trading_symbol, company_name, exchange_token FROM stocks WHERE watchlist_id=?",
        (wid,)
    ).fetchall()
    con.close()

    if not stocks:
        return jsonify([])

    queries = ",".join([f"nse_cm|{s[2]}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q, s in zip(data, stocks):
        out.append({
            "symbol": s[0],
            "company": s[1],
            "ltp": float(q.get("ltp", 0)),
            "change_pct": float(q.get("per_change", 0))
        })
    return jsonify(out)

if __name__ == "__main__":
    app.run()
