import os
import csv
import sqlite3
import time
import requests
import pyotp
from flask import Flask, request, jsonify, render_template

# ================== CONFIG ==================
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DB = "watchlist.db"
BASE_URL = None
SESSION_TOKEN = None
SESSION_SID = None

# ================== APP ==================
app = Flask(__name__)

# ================== DB ==================
def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlists(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS instruments(
        watchlist_id INTEGER,
        exchange_segment TEXT,
        exchange_token TEXT,
        trading_symbol TEXT
    )""")

    if cur.execute("SELECT COUNT(*) FROM watchlists").fetchone()[0] == 0:
        cur.execute("INSERT INTO watchlists(name) VALUES('Watchlist 1')")

    con.commit()
    con.close()

# ================== LOGIN ==================
def kotak_login():
    global BASE_URL, SESSION_TOKEN, SESSION_SID

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

    BASE_URL = r2["data"]["baseUrl"]
    SESSION_TOKEN = r2["data"]["token"]
    SESSION_SID = r2["data"]["sid"]

# ================== LOAD SCRIP MASTER (SEARCH ONLY) ==================
SCRIPS = []
with open("nse_eq_scrip_master.csv", encoding="latin-1") as f:
    SCRIPS = list(csv.DictReader(f))

# ================== ROUTES ==================
@app.route("/")
def index():
    con = db()
    wls = con.execute("SELECT id,name FROM watchlists").fetchall()
    con.close()
    return render_template("index.html", watchlists=wls)

@app.route("/watchlist", methods=["POST"])
def add_watchlist():
    con = db()
    con.execute("INSERT INTO watchlists(name) VALUES(?)", (request.json["name"],))
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

@app.route("/search")
def search():
    q = request.args.get("q","").lower()
    out = []
    for s in SCRIPS:
        if q in s["pTrdSymbol"].lower():
            out.append({
                "exchange_segment": "nse_cm",
                "exchange_token": s["pSymbol"],
                "trading_symbol": s["pTrdSymbol"]
            })
        if len(out) >= 15:
            break
    return jsonify(out)

@app.route("/add", methods=["POST"])
def add_stock():
    d = request.json
    con = db()
    con.execute("""
    INSERT INTO instruments VALUES (?,?,?,?)
    """,(request.args["wid"], d["exchange_segment"], d["exchange_token"], d["trading_symbol"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_stock():
    d = request.json
    con = db()
    con.execute("""
    DELETE FROM instruments
    WHERE watchlist_id=? AND exchange_segment=? AND exchange_token=?
    """,(request.args["wid"], d["exchange_segment"], d["exchange_token"]))
    con.commit()
    con.close()
    return "", 204

@app.route("/prices")
def prices():
    con = db()
    rows = con.execute("""
    SELECT exchange_segment,exchange_token,trading_symbol
    FROM instruments WHERE watchlist_id=?
    """,(request.args["wid"],)).fetchall()
    con.close()

    if not rows:
        return jsonify([])

    q = ",".join([f"{r[0]}|{r[1]}" for r in rows])

    r = requests.get(
        f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}/all",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out = []
    for i,qt in enumerate(r):
        out.append({
            "symbol": rows[i][2],
            "company": qt.get("instrumentName", rows[i][2]),
            "ltp": float(qt["ltp"]),
            "pct": float(qt["per_change"]),
            "volume": qt.get("last_volume","-"),
            "open": qt["ohlc"]["open"],
            "high": qt["ohlc"]["high"],
            "low": qt["ohlc"]["low"],
            "close": qt["ohlc"]["close"],
            "exchange_segment": rows[i][0],
            "exchange_token": rows[i][1]
        })
    return jsonify(out)

# ================== BOOT ==================
init_db()
kotak_login()

if __name__ == "__main__":
    app.run()
