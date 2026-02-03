from flask import Flask, render_template, jsonify, request
import csv, os, requests, pyotp, psycopg2, psycopg2.extras

app = Flask(__name__)

# ---------------- ENV ----------------
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

DATA_FILE = "data/nse_eq_scrip_master.csv"

SESSION = {}
SCRIPS = []

# ---------------- DB ----------------
def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id SERIAL PRIMARY KEY,
            watchlist_id INTEGER REFERENCES watchlists(id) ON DELETE CASCADE,
            trading_symbol TEXT,
            company_name TEXT,
            exchange_token TEXT
        )
    """)

    cur.execute("INSERT INTO watchlists (name) VALUES ('Watchlist 1') ON CONFLICT DO NOTHING")
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
    for r in csv.DictReader(f):
        SCRIPS.append({
            "trading_symbol": r["trading_symbol"],
            "company_name": r["company_name"],
            "exchange_token": r["exchange_token"]
        })

# ---------------- HELPERS ----------------
def format_volume(v):
    v = float(v)
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.2f}K"
    return str(int(v))

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    con = db()
    wl = con.cursor()
    wl.execute("SELECT * FROM watchlists ORDER BY id")
    watchlists = wl.fetchall()
    con.close()
    return render_template("index.html", watchlists=watchlists)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    return jsonify([s for s in SCRIPS if q in s["trading_symbol"].lower()][:10])

@app.route("/watchlist", methods=["POST"])
def create_watchlist():
    con = db()
    con.cursor().execute("INSERT INTO watchlists (name) VALUES (%s)", (request.json["name"],))
    con.commit()
    con.close()
    return "", 204

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    con = db()
    con.cursor().execute("UPDATE watchlists SET name=%s WHERE id=%s", (request.json["name"], wid))
    con.commit()
    con.close()
    return "", 204

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    wid = request.args.get("wid")
    con = db()
    con.cursor().execute("""
        INSERT INTO stocks (watchlist_id, trading_symbol, company_name, exchange_token)
        VALUES (%s, %s, %s, %s)
    """, (wid, s["trading_symbol"], s["company_name"], s["exchange_token"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    con = db()
    con.cursor().execute(
        "DELETE FROM stocks WHERE watchlist_id=%s AND trading_symbol=%s",
        (request.args.get("wid"), request.json["trading_symbol"])
    )
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT trading_symbol, company_name, exchange_token
        FROM stocks WHERE watchlist_id=%s
    """, (wid,))
    stocks = cur.fetchall()
    con.close()

    if not stocks:
        return jsonify([])

    query = ",".join([f"nse_cm|{s['exchange_token']}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{query}/all"

    quotes = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for q, s in zip(quotes, stocks):
        o = q.get("ohlc", {})
        out.append({
            "symbol": s["trading_symbol"],
            "company": s["company_name"],
            "price": round(float(q.get("ltp", 0)), 2),
            "pct": round(float(q.get("per_change", 0)), 2),
            "volume": format_volume(q.get("last_volume", 0)),
            "open": o.get("open", 0),
            "high": o.get("high", 0),
            "low": o.get("low", 0),
            "close": o.get("close", 0)
        })

    return jsonify(out)

if __name__ == "__main__":
    app.run()
