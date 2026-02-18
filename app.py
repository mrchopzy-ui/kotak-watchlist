import os
import json
import sqlite3
import requests
import pyotp
import time
from flask import Flask, render_template, request, jsonify

# =========================
# CONFIG (ENV VARIABLES)
# =========================
ACCESS_TOKEN = os.environ.get("KOTAK_ACCESS_TOKEN")
MOBILE = os.environ.get("KOTAK_MOBILE")
USER_ID = os.environ.get("KOTAK_USER_ID")
MPIN = os.environ.get("KOTAK_MPIN")
TOTP_SECRET = os.environ.get("KOTAK_TOTP_SECRET")

DB_FILE = "watchlists.db"

app = Flask(__name__)

# =========================
# DATABASE
# =========================
def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS watchlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watchlist_id INTEGER,
        symbol TEXT,
        exchange TEXT,
        instrument_type TEXT,
        expiry TEXT,
        strike REAL,
        option_type TEXT
    )
    """)

    db.commit()

init_db()

# =========================
# LOGIN + SESSION
# =========================
SESSION = {}

def kotak_login():
    global SESSION
    if SESSION.get("expires", 0) > time.time():
        return

    totp = pyotp.TOTP(TOTP_SECRET).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi"
        },
        json={
            "mobileNumber": MOBILE,
            "ucc": USER_ID,
            "totp": totp
        }
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

    SESSION = {
        "base": r2["data"]["baseUrl"],
        "sid": r2["data"]["sid"],
        "auth": r2["data"]["token"],
        "expires": time.time() + 300
    }

# =========================
# QUOTES
# =========================
def get_quotes(rows):
    kotak_login()

    symbols = []
    for r in rows:
        symbols.append(f"{r['exchange']}|{r['symbol']}")

    if not symbols:
        return []

    url = f"{SESSION['base']}/script-details/1.0/quotes/neosymbol/" + ",".join(symbols) + "/all"
    resp = requests.get(
        url,
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out = []
    for q in resp:
        out.append({
            "symbol": q.get("display_symbol", ""),
            "company": q.get("instrument_name") or q.get("display_symbol", ""),
            "ltp": float(q.get("ltp", 0)),
            "pct": float(q.get("per_change", 0)),
            "volume": q.get("last_volume", "0"),
            "open": q.get("ohlc", {}).get("open", "0"),
            "high": q.get("ohlc", {}).get("high", "0"),
            "low": q.get("ohlc", {}).get("low", "0"),
            "close": q.get("ohlc", {}).get("close", "0"),
        })

    return out

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    db = get_db()
    wl = db.execute("SELECT id, name FROM watchlists").fetchall()
    if not wl:
        db.execute("INSERT INTO watchlists (name) VALUES ('Watchlist 1')")
        db.commit()
        wl = db.execute("SELECT id, name FROM watchlists").fetchall()
    return render_template("index.html", watchlists=wl)

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    db = get_db()
    rows = db.execute("""
        SELECT symbol, exchange, instrument_type, expiry, strike, option_type
        FROM items WHERE watchlist_id=?
    """, (wid,)).fetchall()

    data = [{
        "symbol": r[0],
        "exchange": r[1],
        "instrument_type": r[2],
        "expiry": r[3],
        "strike": r[4],
        "option_type": r[5]
    } for r in rows]

    return jsonify(get_quotes(data))

@app.route("/add", methods=["POST"])
def add_item():
    wid = request.args.get("wid")
    d = request.json

    db = get_db()
    db.execute("""
        INSERT INTO items
        (watchlist_id, symbol, exchange, instrument_type, expiry, strike, option_type)
        VALUES (?,?,?,?,?,?,?)
    """, (
        wid,
        d["symbol"],
        d["exchange"],
        d["instrument_type"],
        d.get("expiry"),
        d.get("strike"),
        d.get("option_type")
    ))
    db.commit()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_item():
    wid = request.args.get("wid")
    sym = request.json["trading_symbol"]

    db = get_db()
    db.execute(
        "DELETE FROM items WHERE watchlist_id=? AND symbol=?",
        (wid, sym)
    )
    db.commit()
    return "", 204

@app.route("/watchlist", methods=["POST"])
def add_watchlist():
    name = request.json["name"]
    db = get_db()
    db.execute("INSERT INTO watchlists (name) VALUES (?)", (name,))
    db.commit()
    return "", 204

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    name = request.json["name"]
    db = get_db()
    db.execute("UPDATE watchlists SET name=? WHERE id=?", (name, wid))
    db.commit()
    return "", 204

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    app.run(debug=True)
