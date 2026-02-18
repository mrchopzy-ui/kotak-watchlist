import os
import csv
import sqlite3
import requests
from flask import Flask, render_template, jsonify, request

DB_PATH = "data.db"
ACCESS_TOKEN = os.environ.get("KOTAK_ACCESS_TOKEN")

app = Flask(__name__)

# -------------------- DB --------------------
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    c = db()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watchlist_id INTEGER,
        symbol TEXT,
        exch TEXT,
        token TEXT
    )""")

    c.commit()
    c.close()

init_db()

# -------------------- SCRIP MASTER (FO only) --------------------
FO_CONTRACTS = []

def load_fo_master():
    global FO_CONTRACTS
    if FO_CONTRACTS:
        return

    with open("nse_fo_scrip_master.csv", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            FO_CONTRACTS.append(r)

load_fo_master()

# -------------------- HELPERS --------------------
def kotak_quotes(queries):
    url = f"https://mis.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{','.join(queries)}/all"
    r = requests.get(url, headers={"Authorization": ACCESS_TOKEN})
    return r.json()

def volume_fmt(v):
    v = float(v)
    if v >= 1e9: return f"{v/1e9:.2f}B"
    if v >= 1e6: return f"{v/1e6:.2f}M"
    if v >= 1e3: return f"{v/1e3:.2f}K"
    return str(int(v))

# -------------------- ROUTES --------------------
@app.route("/")
def index():
    c = db()
    wl = c.execute("SELECT * FROM watchlists").fetchall()
    c.close()
    return render_template("index.html", watchlists=wl)

@app.route("/watchlist", methods=["POST"])
def create_watchlist():
    data = request.json
    c = db()
    c.execute("INSERT INTO watchlists (name,type) VALUES (?,?)",
              (data["name"], data["type"]))
    c.commit()
    c.close()
    return "", 204

@app.route("/watchlist/<int:i>", methods=["PUT"])
def rename_watchlist(i):
    c = db()
    c.execute("UPDATE watchlists SET name=? WHERE id=?",
              (request.json["name"], i))
    c.commit()
    c.close()
    return "", 204

@app.route("/search")
def search():
    q = request.args.get("q","").upper()
    res = []
    for r in FO_CONTRACTS:
        if r["pTrdSymbol"].startswith(q):
            res.append({
                "symbol": r["pTrdSymbol"],
                "token": r["pSymbol"],
                "exch": r["pExchSeg"]
            })
            if len(res) > 20: break
    return jsonify(res)

@app.route("/add", methods=["POST"])
def add_item():
    d = request.json
    c = db()
    c.execute("INSERT INTO items (watchlist_id,symbol,exch,token) VALUES (?,?,?,?)",
              (d["wid"], d["symbol"], d["exch"], d["token"]))
    c.commit()
    c.close()
    return "", 204

@app.route("/remove", methods=["POST"])
def remove_item():
    d = request.json
    c = db()
    c.execute("DELETE FROM items WHERE watchlist_id=? AND symbol=?",
              (d["wid"], d["symbol"]))
    c.commit()
    c.close()
    return "", 204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    c = db()
    rows = c.execute("SELECT symbol,exch FROM items WHERE watchlist_id=?", (wid,)).fetchall()
    c.close()

    if not rows:
        return jsonify([])

    queries = [f"{r[1]}|{r[0]}" for r in rows]
    q = kotak_quotes(queries)

    out = []
    for r in q:
        out.append({
            "symbol": r["display_symbol"],
            "company": r.get("instrument_name",""),
            "ltp": float(r["ltp"]),
            "pct": float(r["per_change"]),
            "volume": volume_fmt(r.get("last_volume",0)),
            "open": r["ohlc"]["open"],
            "high": r["ohlc"]["high"],
            "low": r["ohlc"]["low"],
            "close": r["ohlc"]["close"]
        })
    return jsonify(out)

if __name__ == "__main__":
    app.run(debug=True)
