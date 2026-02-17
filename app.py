from flask import Flask, render_template, request, jsonify
import csv, sqlite3, os, requests, pyotp, time

app = Flask(__name__)

DB = "watchlist.db"

# ---------- ENV ----------
ACCESS_TOKEN = os.environ["KOTAK_ACCESS_TOKEN"]
MOBILE = os.environ["KOTAK_MOBILE"]
USER_ID = os.environ["KOTAK_USER_ID"]
MPIN = os.environ["KOTAK_MPIN"]
TOTP_SECRET = os.environ["KOTAK_TOTP_SECRET"]

# ---------- LOGIN ----------
def kotak_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()

    r1 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        headers={"Authorization": ACCESS_TOKEN, "neo-fin-key": "neotradeapi"},
        json={"mobileNumber": MOBILE, "ucc": USER_ID, "totp": totp},
    ).json()

    r2 = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
        headers={
            "Authorization": ACCESS_TOKEN,
            "neo-fin-key": "neotradeapi",
            "sid": r1["data"]["sid"],
            "Auth": r1["data"]["token"],
        },
        json={"mpin": MPIN},
    ).json()

    return r2["data"]["baseUrl"]

BASE_URL = kotak_login()

# ---------- DB ----------
def db():
    return sqlite3.connect(DB)

with db() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS watchlists(id INTEGER PRIMARY KEY, name TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS stocks(
        wid INTEGER, symbol TEXT, exchange TEXT, segment TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO watchlists VALUES(1,'Watchlist 1')")

# ---------- LOAD SCRIP MASTERS ----------
EQ_SCRIPS = []
FO_SCRIPS = []

with open("nse_eq_scrip_master.csv", encoding="latin-1") as f:
    EQ_SCRIPS = list(csv.DictReader(f))

with open("nse_fo_scrip_master.csv", encoding="latin-1") as f:
    FO_SCRIPS = list(csv.DictReader(f))

# ---------- ROUTES ----------
@app.route("/")
def index():
    with db() as c:
        tabs = c.execute("SELECT * FROM watchlists").fetchall()
    return render_template("index.html", tabs=tabs)

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    results = []

    for s in EQ_SCRIPS:
        if q in s["trading_symbol"].lower():
            results.append({
                "symbol": s["trading_symbol"],
                "exchange": "nse_cm",
                "segment": "EQ"
            })

    for s in FO_SCRIPS:
        if q in s["trading_symbol"].lower():
            results.append({
                "symbol": s["trading_symbol"],
                "exchange": "nse_fo",
                "segment": "FO"
            })

    return jsonify(results[:20])

@app.route("/add", methods=["POST"])
def add():
    wid = request.args.get("wid")
    s = request.json
    with db() as c:
        c.execute(
            "INSERT INTO stocks VALUES(?,?,?,?)",
            (wid, s["symbol"], s["exchange"], s["segment"]),
        )
    return ("", 204)

@app.route("/remove", methods=["POST"])
def remove():
    wid = request.args.get("wid")
    sym = request.json["symbol"]
    with db() as c:
        c.execute("DELETE FROM stocks WHERE wid=? AND symbol=?", (wid, sym))
    return ("", 204)

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    with db() as c:
        rows = c.execute(
            "SELECT symbol,exchange,segment FROM stocks WHERE wid=?", (wid,)
        ).fetchall()

    out = []
    for sym, exch, seg in rows:
        q = f"{exch}|{sym}"
        r = requests.get(
            f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}",
            headers={"Authorization": ACCESS_TOKEN},
        ).json()[0]

        out.append({
            "symbol": sym,
            "company": r.get("instrumentName", sym),
            "ltp": float(r["ltp"]),
            "pct": float(r["per_change"]),
        })

    return jsonify(out)

@app.route("/watchlist", methods=["POST"])
def new_watchlist():
    name = request.json["name"]
    with db() as c:
        c.execute("INSERT INTO watchlists(name) VALUES(?)", (name,))
    return ("", 204)

@app.route("/watchlist/<int:wid>", methods=["PUT"])
def rename(wid):
    name = request.json["name"]
    with db() as c:
        c.execute("UPDATE watchlists SET name=? WHERE id=?", (name, wid))
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True)
