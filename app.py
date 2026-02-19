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

def db():
    return sqlite3.connect(DB_FILE)

def init_db():
    con = db()
    cur = con.cursor()
    # Watchlist table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlists(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    # Stocks in watchlist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER,
            trading_symbol TEXT,
            exchange_token TEXT,
            exchange_segment TEXT
        )
    """)
    # NEW: Scrip Master table to save memory
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scrip_master(
            trading_symbol TEXT,
            exchange_token TEXT,
            exchange_segment TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON scrip_master(trading_symbol)")
    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

def login_and_fetch_scrips():
    # 1. Login
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
    
    # 2. Fetch Scrip Paths
    scrip_url = f"{SESSION['base']}/script-details/1.0/masterscrip/file-paths"
    file_data = requests.get(scrip_url, headers={"Authorization": ACCESS_TOKEN}).json()
    
    target_segments = ["nse_cm", "bse_cm", "nse_fo", "bse_fo"]
    
    con = db()
    con.execute("DELETE FROM scrip_master") # Clear old data
    
    for file_path in file_data["data"]["filesPaths"]:
        segment = next((s for s in target_segments if s in file_path), None)
        if segment:
            # Stream the file to keep memory low
            r = requests.get(file_path, stream=True)
            f = io.StringIO(r.content.decode('latin-1'))
            reader = csv.DictReader(f)
            
            # Insert in batches for speed
            batch = []
            for row in reader:
                batch.append((row["pTrdSymbol"], row["pSymbol"], segment))
                if len(batch) > 1000:
                    con.executemany("INSERT INTO scrip_master VALUES (?, ?, ?)", batch)
                    batch = []
            if batch:
                con.executemany("INSERT INTO scrip_master VALUES (?, ?, ?)", batch)
    
    con.commit()
    con.close()

# Initialize
init_db()
login_and_fetch_scrips()

@app.route("/")
def index():
    con = db()
    rows = con.execute("SELECT id, name FROM watchlists ORDER BY id").fetchall()
    con.close()
    return render_template("index.html", watchlists=rows)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip().upper()
    if not q: return jsonify([])
    
    con = db()
    # Search DB instead of RAM. We look for symbols STARTING with the query first.
    rows = con.execute("""
        SELECT trading_symbol, exchange_token, exchange_segment 
        FROM scrip_master 
        WHERE trading_symbol LIKE ? 
        ORDER BY (CASE WHEN trading_symbol LIKE ? THEN 0 ELSE 1 END), length(trading_symbol)
        LIMIT 15
    """, (f'%{q}%', f'{q}%')).fetchall()
    con.close()
    
    result = [{"trading_symbol": r[0], "exchange_token": r[1], "exchange_segment": r[2]} for r in rows]
    return jsonify(result)

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

    queries = ",".join([f"{s[2]}|{s[1]}" for s in stocks])
    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/{queries}/all"
    resp = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    # Normalize response to list
    data = resp if isinstance(resp, list) else [resp]

    out = []
    def format_vol(v):
        try:
            v = float(v)
            if v >= 1e9: return f"{v/1e9:.2f}B"
            if v >= 1e6: return f"{v/1e6:.2f}M"
            if v >= 1e3: return f"{v/1e3:.2f}K"
            return str(int(v))
        except: return "0"

    for q, s in zip(data, stocks):
        o = q.get("ohlc", {})
        out.append({
            "symbol": s[0],
            "company_name": q.get("instrumentName", s[0]),
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0)),
            "volume": format_vol(q.get("last_volume", 0)),
            "open": o.get("open", 0), "high": o.get("high", 0),
            "low": o.get("low", 0), "close": o.get("close", 0)
        })
    return jsonify(out)

@app.route("/add", methods=["POST"])
def add_stock():
    s, wid = request.json, request.args.get("wid")
    con = db()
    con.execute("INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token, exchange_segment) VALUES (?, ?, ?, ?)",
                (wid, s["trading_symbol"], s["exchange_token"], s["exchange_segment"]))
    con.commit(); con.close()
    return "", 204

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
