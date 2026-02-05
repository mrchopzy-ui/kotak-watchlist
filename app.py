import os
import csv
import json
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, g

# =========================================================
# APP SETUP
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "watchlists.db")
COMPANY_MASTER = os.path.join(DATA_DIR, "company_master.csv")

os.makedirs(DATA_DIR, exist_ok=True)

IS_RENDER = os.environ.get("RENDER") == "true"

# =========================================================
# DATABASE
# =========================================================

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER,
            symbol TEXT,
            FOREIGN KEY (watchlist_id) REFERENCES watchlists(id)
        )
    """)
    db.commit()

with app.app_context():
    init_db()

# =========================================================
# LOAD COMPANY MASTER (SAFE)
# =========================================================

COMPANY_MAP = {}

def load_company_master():
    global COMPANY_MAP
    if not os.path.exists(COMPANY_MASTER):
        print("⚠️ company_master.csv not found")
        return

    with open(COMPANY_MASTER, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            COMPANY_MAP[row["symbol"]] = row["company_name"]

    print(f"✅ Loaded {len(COMPANY_MAP)} company names")

load_company_master()

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    q = request.args.get("q", "").upper()
    results = []

    for symbol, name in COMPANY_MAP.items():
        if q in symbol:
            results.append({
                "symbol": symbol,
                "company_name": name
            })
        if len(results) >= 20:
            break

    return jsonify(results)

@app.route("/watchlists")
def get_watchlists():
    db = get_db()
    rows = db.execute("SELECT * FROM watchlists").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/watchlists", methods=["POST"])
def add_watchlist():
    name = request.json.get("name", "Watchlist")
    db = get_db()
    db.execute("INSERT INTO watchlists (name) VALUES (?)", (name,))
    db.commit()
    return ("", 204)

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename_watchlist(wid):
    name = request.json.get("name")
    db = get_db()
    db.execute("UPDATE watchlists SET name=? WHERE id=?", (name, wid))
    db.commit()
    return ("", 204)

@app.route("/add", methods=["POST"])
def add_stock():
    wid = request.args.get("wid")
    symbol = request.json.get("symbol")

    db = get_db()
    db.execute(
        "INSERT INTO watchlist_items (watchlist_id, symbol) VALUES (?, ?)",
        (wid, symbol)
    )
    db.commit()
    return ("", 204)

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    db = get_db()

    rows = db.execute("""
        SELECT symbol FROM watchlist_items WHERE watchlist_id=?
    """, (wid,)).fetchall()

    data = []
    for r in rows:
        symbol = r["symbol"]
        data.append({
            "symbol": symbol,
            "company_name": COMPANY_MAP.get(symbol, symbol),
            "price": 0,
            "change": 0
        })

    return jsonify(data)

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
