import os
import csv
import sqlite3
import requests
import pyotp
import logging
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- CONFIGURATION & ENV VARS ---
KOTAK_USER_ID = os.environ.get("KOTAK_USER_ID")
KOTAK_MPIN = os.environ.get("KOTAK_MPIN")
KOTAK_MOBILE = os.environ.get("KOTAK_MOBILE")
KOTAK_TOTP_SECRET = os.environ.get("KOTAK_TOTP_SECRET")
KOTAK_ACCESS_TOKEN = os.environ.get("KOTAK_ACCESS_TOKEN")

# Global Session State
api_session = {
    "token": None,
    "base_url": "https://tradeapi.kotaksecurities.com/apim",
    "sid": None
}

# --- DATABASE SETUP ---
DB_NAME = "watchlists.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS watchlists 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stocks 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      watchlist_id INTEGER, 
                      trading_symbol TEXT, 
                      exchange_token TEXT)''')
        c.execute("SELECT count(*) FROM watchlists")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO watchlists (name) VALUES (?)", ("Default",))
        conn.commit()

init_db()

# --- CSV LOADING (ROBUST FIX) ---
SCRIP_MASTER = []

def load_scrip_master():
    """Loads NSE scrip master with Latin-1 encoding and robust header checking."""
    global SCRIP_MASTER
    SCRIP_MASTER = [] # Reset
    try:
        with open("nse_eq_scrip_master.csv", mode='r', encoding='latin-1') as f:
            # Read first line to normalize headers
            reader = csv.DictReader(f)
            
            # Print detected headers for debugging
            if reader.fieldnames:
                print(f"📄 CSV Headers Detected: {reader.fieldnames}")

            for row in reader:
                # robustly find symbol/token keys regardless of case
                r_lower = {k.lower(): v for k, v in row.items()}
                
                sym = r_lower.get("symbol", r_lower.get("symbol_ticker", "")).strip()
                tok = r_lower.get("token", r_lower.get("token_id", "")).strip()

                if sym and tok:
                    SCRIP_MASTER.append({"symbol": sym, "token": tok})
        
        print(f"✅ Loaded {len(SCRIP_MASTER)} scrips. Sample: {SCRIP_MASTER[:3]}")
    except FileNotFoundError:
        print("❌ ERROR: nse_eq_scrip_master.csv not found in root directory.")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")

load_scrip_master()

# --- KOTAK AUTH FLOW ---
def kotak_login():
    global api_session
    if not KOTAK_USER_ID or not KOTAK_ACCESS_TOKEN:
        print("⚠️  Auth env vars missing. Skipping login.")
        return False

    totp = pyotp.TOTP(KOTAK_TOTP_SECRET).now()
    headers = {"Authorization": f"Bearer {KOTAK_ACCESS_TOKEN}", "Content-Type": "application/json"}
    login_url = "https://tradeapi.kotaksecurities.com/apim/session/1.0/session/login/userid"
    
    try:
        # 1. Login
        r1 = requests.post(login_url, json={"userid": KOTAK_USER_ID, "password": totp}, headers=headers)
        
        # 2. Validate
        validate_url = "https://tradeapi.kotaksecurities.com/apim/session/1.0/session/2FA/oneStep"
        r2 = requests.post(validate_url, json={"userid": KOTAK_USER_ID, "mpin": KOTAK_MPIN}, headers=headers)
        data = r2.json()
        
        if "sessionToken" in data:
            api_session["token"] = data["sessionToken"]
            print("✅ Kotak Login Successful")
            return True
        else:
            print(f"❌ Login Failed: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        return False

kotak_login()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_scrip():
    query = request.args.get('q', '').upper().strip()
    if not query:
        return jsonify([])
    
    if not SCRIP_MASTER:
        # Debugging: let frontend know backend has no data
        print("⚠️ Search called but SCRIP_MASTER is empty.")
        return jsonify([])

    # Filter: strict startswith or contains
    results = [s for s in SCRIP_MASTER if query in s['symbol'].upper()][:10]
    return jsonify(results)

@app.route('/api/watchlist')
def get_watchlist():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id, trading_symbol, exchange_token FROM stocks")
        rows = c.fetchall()
    
    if not rows:
        return jsonify([])

    tokens = [f"nse_cm|{r[2]}" for r in rows]
    token_string = ",".join(tokens)
    
    if not api_session["token"]:
        kotak_login()
        
    url = f"{api_session['base_url']}/script-details/1.0/quotes/neosymbol/{token_string}"
    headers = {
        "Authorization": f"Bearer {KOTAK_ACCESS_TOKEN}",
        "sessionToken": api_session["token"],
        "sid": "render_instance"
    }
    
    stocks_data = []
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        # Handle if API returns a single dict instead of list
        if isinstance(data, dict) and "message" in data:
             raise Exception(data["message"])
        
        if not isinstance(data, list):
            data = [data] # Normalize to list

        for row in rows:
            db_id, symbol, token = row
            quote = next((item for item in data if item.get('instrumentToken') == token), None)
            
            if quote:
                stocks_data.append({
                    "id": db_id,
                    "symbol": symbol,
                    "name": quote.get("instrumentName", symbol),
                    "ltp": quote.get("lastPrice", 0),
                    "change": quote.get("change", 0),
                    "volume": quote.get("volume", 0),
                    "ohlc": f"O:{quote.get('open')} H:{quote.get('high')} L:{quote.get('low')}"
                })
            else:
                stocks_data.append({"id": db_id, "symbol": symbol, "name": "Loading...", "ltp": "-", "change": "-", "volume": "-", "ohlc": "-"})
                
    except Exception as e:
        print(f"Quote API Error: {e}")
        for row in rows:
            stocks_data.append({"id": row[0], "symbol": row[1], "name": "API Error", "ltp":0, "change":0, "volume":0, "ohlc":"-"})

    return jsonify(stocks_data)

@app.route('/api/add', methods=['POST'])
def add_stock():
    data = request.json
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM stocks WHERE exchange_token = ?", (data.get('token'),))
        if not c.fetchone():
            c.execute("INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token) VALUES (?, ?, ?)", 
                      (1, data.get('symbol'), data.get('token')))
            conn.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "exists"})

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_stock(id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM stocks WHERE id = ?", (id,))
        conn.commit()
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    app.run(debug=True)
