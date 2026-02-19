import os
import csv
import time
import sqlite3
import requests
import pyotp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB = "watchlist.db"

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB, check_same_thread=False)

with db() as c:
    c.execute("""
    CREATE TABLE IF NOT EXISTS watchlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        wid INTEGER,
        symbol TEXT
    )
    """)
    if c.execute("SELECT COUNT(*) FROM watchlists").fetchone()[0] == 0:
        c.execute("INSERT INTO watchlists (name) VALUES ('Watchlist 1')")

# ---------------- LOAD SCRIP MASTER (SEARCH ONLY) ----------------
with open("nse_eq_scrip_master.csv", encoding="latin-1") as f:
    SCRIPS = list(csv.DictReader(f))

# ---------------- KOTAK LOGIN ----------------
def kotak_headers():
    return {
        "Authorization": os.environ["KOTAK_ACCESS_TOKEN"],
        "neo-fin-key": "neotradeapi"
    }

def kotak_login():
    totp = pyotp.TOTP(os.environ["KOTAK_TOTP_SECRET"]).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers=kotak_headers(),
        json={
            "mobileNumber": os.environ["KOTAK_MOBILE"],
            "ucc": os.environ["KOTAK_USER_ID"],
            "totp": totp
        }
    ).json()

    r2 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
        headers={
            **kotak_headers(),
            "sid": r1["data"]["sid"],
            "Auth": r1["data"]["token"]
        },
        json={"mpin": os.environ["KOTAK_MPIN"]}
    ).json()

    return r2["data"]["baseUrl"], r2["data"]["token"], r2["data"]["sid"]

BASE, AUTH, SID = kotak_login()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    wls = db().execute("SELECT id,name FROM watchlists").fetchall()
    return render_template("index.html", watchlists=wls)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    res = []
    for s in SCRIPS:
        if q in s["trading_symbol"].lower():
            res.append(s)
        if len(res) == 10:
            break
    return jsonify(res)

@app.route("/add", methods=["POST"])
def add():
    wid = request.args.get("wid")
    sym = request.json["trading_symbol"]
    db().execute("INSERT INTO stocks VALUES (?,?)", (wid, sym))
    db().commit()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove():
    wid = request.args.get("wid")
    sym = request.json["trading_symbol"]
    db().execute("DELETE FROM stocks WHERE wid=? AND symbol=?", (wid, sym))
    db().commit()
    return "", 204

@app.route("/watchlist", methods=["POST"])
def add_watchlist():
    db().execute("INSERT INTO watchlists (name) VALUES (?)", (request.json["name"],))
    db().commit()
    return "", 204

@app.route("/watchlist/<wid>", methods=["PUT"])
def rename_watchlist(wid):
    db().execute("UPDATE watchlists SET name=? WHERE id=?", (request.json["name"], wid))
    db().commit()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    syms = [x[0] for x in db().execute("SELECT symbol FROM stocks WHERE wid=?", (wid,))]
    if not syms:
        return jsonify([])

    q = ",".join([f"nse_cm|{s.replace('-EQ','')}" for s in syms])
    r = requests.get(
        f"{BASE}/script-details/1.0/quotes/neosymbol/{q}/all",
        headers={"Authorization": os.environ["KOTAK_ACCESS_TOKEN"]}
    ).json()

    out = []
    for x in r:
        out.append({
            "symbol": x["exchange_token"] + "-EQ",
            "company": x.get("instrument_name",""),
            "ltp": float(x["ltp"]),
            "pct": float(x["per_change"]),
            "volume": x["last_volume"],
            "open": x["ohlc"]["open"],
            "high": x["ohlc"]["high"],
            "low": x["ohlc"]["low"],
            "close": x["ohlc"]["close"]
        })
    return jsonify(out)

if __name__ == "__main__":
    app.run()
