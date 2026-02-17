import sqlite3, csv, os, time
from flask import Flask, jsonify, request, render_template
import requests

DB = "watchlist.db"
SCRIP_MASTER = "nse_all_scrips.csv"

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")

app = Flask(__name__)

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB, check_same_thread=False)

def migrate():
    c = db().cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS watchlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watchlist_id INTEGER,
        instrument_type TEXT,
        exchange_segment TEXT,
        exchange_token TEXT,
        symbol TEXT,
        display_name TEXT,
        expiry TEXT,
        strike REAL,
        option_type TEXT,
        isin TEXT
    )
    """)
    if c.execute("SELECT COUNT(*) FROM watchlists").fetchone()[0] == 0:
        c.execute("INSERT INTO watchlists(name) VALUES ('Watchlist 1')")
    c.connection.commit()

migrate()

# ---------------- LOAD SCRIP MASTER ----------------
if not os.path.exists(SCRIP_MASTER):
    raise RuntimeError("❌ Missing nse_all_scrips.csv")

with open(SCRIP_MASTER, encoding="latin-1") as f:
    SCRIPS = list(csv.DictReader(f))

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    wls = db().execute("SELECT id,name FROM watchlists").fetchall()
    return render_template("index.html", watchlists=wls)

@app.route("/search")
def search():
    q = request.args.get("q","").lower()
    out = []
    for r in SCRIPS:
        if q in r["display_name"].lower():
            out.append(r)
        if len(out) == 20: break
    return jsonify(out)

@app.route("/add", methods=["POST"])
def add():
    wid = request.args["wid"]
    d = request.json
    db().execute("""
    INSERT INTO watchlist_items
    (watchlist_id,instrument_type,exchange_segment,exchange_token,
     symbol,display_name,expiry,strike,option_type,isin)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """,(
        wid, d["type"], d["segment"], d["token"],
        d["symbol"], d["display_name"],
        d.get("expiry"), d.get("strike"),
        d.get("option_type"), d.get("isin")
    ))
    db().commit()
    return "",204

@app.route("/remove", methods=["POST"])
def remove():
    db().execute("DELETE FROM watchlist_items WHERE id=?", (request.json["id"],))
    db().commit()
    return "",204

@app.route("/prices")
def prices():
    wid = request.args["wid"]
    rows = db().execute("""
    SELECT id,exchange_segment,exchange_token,symbol,display_name
    FROM watchlist_items WHERE watchlist_id=?
    """,(wid,)).fetchall()

    if not rows: return jsonify([])

    q = ",".join([f"{r[1]}|{r[2]}" for r in rows])
    res = requests.get(
        f"https://e22.kotaksecurities.com/script-details/1.0/quotes/neosymbol/{q}/all",
        headers={"Authorization": ACCESS_TOKEN}
    ).json()

    out=[]
    for r,d in zip(rows,res):
        out.append({
            "id": r[0],
            "symbol": r[3],
            "name": r[4],
            "ltp": float(d["ltp"]),
            "pct": float(d["per_change"]),
            "volume": d.get("last_volume","0")
        })
    return jsonify(out)

@app.route("/watchlist", methods=["POST"])
def add_wl():
    db().execute("INSERT INTO watchlists(name) VALUES (?)",
                 (request.json["name"],))
    db().commit()
    return "",204
