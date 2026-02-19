from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp, io

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

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
            exchange_segment TEXT
        )
    """)
    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

def login_and_fetch_scrips():
    global SCRIPS
    # Step 1: TOTP Login
    totp = pyotp.TOTP(TOTP_SECRET).now()
    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={"Authorization": ACCESS_TOKEN, "neo-fin-key": "neotradeapi"},
        json={"mobileNumber": MOBILE, "ucc": USER_ID, "totp": totp}
    ).json()

    # Step 2: MPIN Validate
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
    
    # Step 3: Get Master Scrip File Paths
    # We fetch ALL segments to support F&O
    scrip_url = f"{SESSION['base']}/script-details/1.0/masterscrip/file-paths"
    file_data = requests.get(scrip_url, headers={"Authorization": ACCESS_TOKEN}).json()
    
    all_scrips = []
    # Segments to include: nse_cm, bse_cm, nse_fo, bse_fo
    target_segments = ["nse_cm", "bse_cm", "nse_fo", "bse_fo"]
    
    for file_path in file_data["data"]["filesPaths"]:
        segment = next((s for s in target_segments if s in file_path), None)
        if segment:
            r = requests.get(file_path)
            # Use latin-1 to prevent crashes as established in v2
            f = io.StringIO(r.content.decode('latin-1'))
            reader = csv.DictReader(f)
            for row in reader:
                row["exchange_segment"] = segment # Tag each scrip with its segment
                all_scrips.append(row)
    
    SCRIPS = all_scrips

# Initialize
init_db()
login_and_fetch_scrips()

def get_watchlists():
    con = db()
    rows = con.execute("SELECT id, name FROM watchlists ORDER BY id").fetchall()
    con.close()
    return rows

def format_volume(v):
    try:
        v = float(v)
        if v >= 1_000_000_000: return f"{v/1_000_000_000:.2f}B"
        if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
        if v >= 1_000: return f"{v/1_000:.2f}K"
        return str(int(v))
    except: return "0"

@app.route("/")
def index():
    return render_template("index.html", watchlists=get_watchlists())

@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if not q: return jsonify([])
    
    # Intelligent sorting from our previous update
    matches = [s for s in SCRIPS if q in s["pTrdSymbol"].lower()]
    matches.sort(key=lambda s: (not s["pTrdSymbol"].lower().startswith(q), len(s["pTrdSymbol"])))
    
    # Convert Scrip Master keys to our frontend keys
    result = []
    for m in matches[:15]:
        result.append({
            "trading_symbol": m["pTrdSymbol"],
            "exchange_token": m["pSymbol"],
            "exchange_segment": m["exchange_segment"]
        })
    return jsonify(result)

@app.route("/add", methods=["POST"])
def add_stock():
    s = request.json
    wid = request.args.get("wid")
    con = db()
    con.execute("""
        INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token, exchange_segment)
        VALUES (?, ?, ?, ?)
    """, (wid, s["trading_symbol"], s["exchange_token"], s["exchange_segment"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    con = db()
    stocks = con.execute(
        "SELECT trading_symbol, exchange_token, exchange_segment FROM stocks WHERE watchlist_id=?",
        (wid,)
    ).fetchall()
    con.close()

    if not stocks: return jsonify([])

    # Kotak Quotes API requires segment|token format
    queries = ",".join([f"{s[2]}|{s[1]}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"
    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    # Ensure data is a list (Quotes API returns a list of dicts)
    if isinstance(data, dict): data = [data]

    for q, s in zip(data, stocks):
        o = q.get("ohlc", {})
        out.append({
            "symbol": s[0],
            "company_name": q.get("instrumentName", s[0]),
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0)),
            "volume": format_volume(q.get("last_volume", 0)),
            "open": o.get("open", 0),
            "high": o.get("high", 0),
            "low": o.get("low", 0),
            "close": o.get("close", 0)
        })
    return jsonify(out)

# Keep your other routes (remove, watchlist, rename) exactly as they were
@app.route("/remove", methods=["POST"])
def remove_stock():
    con = db()
    con.execute("DELETE FROM stocks WHERE watchlist_id=? AND trading_symbol=?",
                (request.args.get("wid"), request.json["trading_symbol"]))
    con.commit(); con.close()
    return "", 204

@app.route("/watchlist", methods=["POST"])
def create_watchlist():
    con = db()
    con.execute("INSERT INTO watchlists(name) VALUES (?)", (request.json["name"],))
    con.commit(); con.close()
    return "", 204

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    con = db()
    con.execute("UPDATE watchlists SET name=? WHERE id=?", (request.json["name"], wid))
    con.commit(); con.close()
    return "", 204

if __name__ == "__main__":
    app.run()
