from flask import Flask, render_template, jsonify, request
import csv, os, sqlite3, requests, pyotp

app = Flask(__name__)

# ---------------- ENV ----------------
ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

DATA_FILE = "data/nse_eq_scrip_master.csv"
DB_FILE = "watchlists.db"

SESSION = {}
SCRIPS = []

# ---------------- DB ----------------
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
            company_name TEXT,
            exchange_token TEXT
        )
    """)
    cur.execute("INSERT OR IGNORE INTO watchlists(name) VALUES ('Watchlist 1')")
    con.commit()
    con.close()

init_db()

# ---------------- LOGIN ----------------
def login():
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

login()

# ---------------- LOAD SCRIP MASTER ----------------
with open(DATA_FILE, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        SCRIPS.append({
            "trading_symbol": r["trading_symbol"],
            "company_name": r["company_name"],
            "exchange_token": r["exchange_token"]
        })

# ---------------- HELPERS ----------------
def get_watchlists():
    con = db()
    rows = con.execute("SELECT id, name FROM
