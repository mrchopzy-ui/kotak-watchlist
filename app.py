import os, csv, sqlite3, requests, pyotp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ---------- ENV ----------
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
MOBILE = os.environ["MOBILE"]
USER_ID = os.environ["USER_ID"]
MPIN = os.environ["MPIN"]
TOTP_SECRET = os.environ["TOTP_SECRET"]

# ---------- DB ----------
conn = sqlite3.connect("watchlist.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS items (
    wid INTEGER,
    exch TEXT,
    token TEXT,
    symbol TEXT,
    type TEXT
)
""")
conn.commit()

# ---------- LOGIN ----------
def kotak_login():
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

    return r2["data"]["baseUrl"]

BASE_URL = kotak_login()

# ---------- LOAD SCRIP MASTERS ----------
SCRIPS = []

def load_csv(path, exch, default_type):
    with open(path, encoding="latin-1") as f:
        for r in csv.DictReader(f):
            SCRIPS.append({
                "symbol": r["pTrdSymbol"],
                "token": r["pSymbol"],
                "exch": exch,
                "type": r.get("optionType") or default_type
            })

# Equity + Index
load_csv("nse_eq_scrip_master.csv", "nse_cm", "EQ")

# Futures & Options
load_csv("nse_fo_scrip_master.csv", "nse_fo", "FNO")

# ---------- ROUTES ----------
@app.route("/")
def index():
    cur.execute("SELECT * FROM watchlists")
    wls = cur.fetchall()
    if not wls:
        cur.execute("INSERT INTO watchlists (name) VALUES ('Watchlist 1')")
        conn.commit()
        return index()
    return render_template("index.html", watchlists=wls)

@app.route("/search")
def search():
    q = request.args.get("q","").upper()
    res = []

    for s in SCRIPS:
        if q in s["symbol"]:
            res.append(s)
        if len(res) == 25:
            break
    return jsonify(res)

@app.route("/add", methods=["POST"])
def add():
    d = request.json
    wid = request.args.get("wid")
    cur.execute(
        "INSERT INTO items VALUES (?,?,?,?,?)",
        (wid, d["exch"], d["token"], d["symbol"], d["type"])
    )
    conn.commit()
    return "",204

@app.route("/remove", methods=["POST"])
def remove():
    d = request.json
    wid = request.args.get("wid")
    cur.execute("DELETE FROM items WHERE wid=? AND symbol=?", (wid, d["symbol"]))
    conn.commit()
    return "",204

@app.route("/prices")
def prices():
    wid = request.args.get("wid")
    cur.execute("SELECT * FROM items WHERE wid=?", (wid,))
    rows = cur.fetchall()
    if not rows:
        return jsonify([])

    q = ",".join([f"{r[1]}|{r[2]}" for r in rows])
    url = f"{BASE_URL}/script-details/1.0/quotes/neosymbol/{q}/all"

    data = requests.get(url, headers={"Authorization": ACCESS_TOKEN}).json()

    out = []
    for r, qd in zip(rows, data):
        out.append({
            "symbol": r[3],
            "company": qd.get("instrumentName",""),
            "ltp": float(qd.get("ltp",0)),
            "pct": float(qd.get("per_change",0)),
            "type": r[4]
        })
    return jsonify(out)

@app.route("/watchlist", methods=["POST"])
def new_watchlist():
    cur.execute("INSERT INTO watchlists (name) VALUES ('New Watchlist')")
    conn.commit()
    return "",204

@app.route("/watchlist/<wid>", methods=["PUT"])
def rename(wid):
    cur.execute("UPDATE watchlists SET name=? WHERE id=?", (request.json["name"], wid))
    conn.commit()
    return "",204
