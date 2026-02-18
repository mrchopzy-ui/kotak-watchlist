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

CONSUMER_KEY = os.environ.get("KOTAK_CONSUMER_KEY") # Sometimes needed depending on specific API setup, usually implied by Access Token in v3 but keeping placeholder if needed.
# Note: In v3 simplified, Access Token often acts as the key. We will use the provided Access Token header.

# Global Session State
api_session = {
    "token": None,
    "base_url": "https://tradeapi.kotaksecurities.com/apim", # Default, updated after login
    "sid": None
}

# --- DATABASE SETUP ---
DB_NAME = "watchlists.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Watchlists table
        c.execute('''CREATE TABLE IF NOT EXISTS watchlists 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
        # Stocks table (NO company_name stored here)
        c.execute('''CREATE TABLE IF NOT EXISTS stocks 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      watchlist_id INTEGER, 
                      trading_symbol TEXT, 
                      exchange_token TEXT)''')
        
        # Create default watchlist if none exists
        c.execute("SELECT count(*) FROM watchlists")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO watchlists (name) VALUES (?)", ("Default",))
        conn.commit()

init_db()

# --- CSV LOADING (CRITICAL FIX) ---
SCRIP_MASTER = []

def load_scrip_master():
    """Loads NSE scrip master with Latin-1 encoding to prevent Linux crashes."""
    global SCRIP_MASTER
    try:
        # v2 FIX: encoding='latin-1'
        with open("nse_eq_scrip_master.csv", mode='r', encoding='latin-1') as f:
            reader = csv.DictReader(f)
            # Expecting CSV headers like: exchange,symbol,token (adjust based on your actual CSV)
            # We map them to a standard structure
            for row in reader:
                # Basic check to ensure it's an equity
                SCRIP_MASTER.append({
                    "symbol": row.get("symbol", "").strip(),
                    "token": row.get("token", "").strip()
                })
        print(f"✅ Loaded {len(SCRIP_MASTER)} scrips from CSV.")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")

load_scrip_master()

# --- KOTAK AUTH FLOW ---
def kotak_login():
    """Performs 2-step login: Login (TOTP) -> Validate (MPIN)."""
    global api_session
    
    # 1. Generate TOTP
    totp = pyotp.TOTP(KOTAK_TOTP_SECRET).now()
    
    headers = {
        "Authorization": f"Bearer {KOTAK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Login via Mobile/TOTP
    login_url = "https://tradeapi.kotaksecurities.com/apim/session/1.0/session/login/userid"
    payload_1 = {
        "userId": KOTAK_USER_ID,
        "password": KOTAK_MOBILE # Using Mobile as pwd for this flow usually, or specific pwd
    }
    
    # NOTE: Adjusting payload based on standard v3 TOTP flow logic
    # If using strictly the environment variables provided:
    # We assume standard flow: POST login -> GET valid details
    
    try:
        # This implementation assumes the standard tradeApiLogin logic
        # For brevity, implementing the crucial validation step which returns the BaseURL
        
        # 1. Login
        r1 = requests.post(login_url, json={"userid": KOTAK_USER_ID, "password": totp}, headers=headers)
        
        # 2. Validate with MPIN (This is usually where we get the SID and BaseURL)
        validate_url = "https://tradeapi.kotaksecurities.com/apim/session/1.0/session/2FA/oneStep"
        payload_2 = {
            "userid": KOTAK_USER_ID,
            "mpin": KOTAK_MPIN
        }
        
        r2 = requests.post(validate_url, json=payload_2, headers=headers)
        data = r2.json()
        
        if "sessionToken" in data:
            api_session["token"] = data["sessionToken"]
            # Capture Dynamic Base URL if provided, else keep default
            # Some APIs return 'serviceUrl' or similar. 
            # If not provided, we stick to the main endpoint.
            print("✅ Kotak Login Successful")
            return True
        else:
            print(f"❌ Login Failed: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        return False

# Attempt login on startup
kotak_login()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_scrip():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify([])
    
    # Filter memory list
    results = [s for s in SCRIP_MASTER if query in s['symbol']][:10]
    return jsonify(results)

@app.route('/api/watchlist')
def get_watchlist():
    # 1. Get stocks from DB
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id, trading_symbol, exchange_token FROM stocks")
        rows = c.fetchall()
    
    if not rows:
        return jsonify([])

    # 2. Construct Quote API Payload
    # Format: nse_cm|token,nse_cm|token...
    tokens = [f"nse_cm|{r[2]}" for r in rows]
    token_string = ",".join(tokens)
    
    # 3. Call Kotak Quotes API
    if not api_session["token"]:
        kotak_login() # Retry login if missing
        
    url = f"{api_session['base_url']}/script-details/1.0/quotes/neosymbol/{token_string}"
    headers = {
        "Authorization": f"Bearer {KOTAK_ACCESS_TOKEN}",
        "sessionToken": api_session["token"],
        "sid": "render_instance" # Arbitrary SID if not strictly enforced
    }
    
    stocks_data = []
    
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        
        # 4. Map DB rows to API response
        # We match based on the instrumentToken usually found in response
        
        # Note: API response structure varies. Assuming list of objects.
        # We iterate our DB rows and find matching data in response
        
        for row in rows:
            db_id, symbol, token = row
            
            # Find matching item in API response
            # Implementation depends on exact API shape. Assuming standard list.
            quote = next((item for item in data if item.get('instrumentToken') == token), None)
            
            if quote:
                stocks_data.append({
                    "id": db_id,
                    "symbol": symbol,
                    "name": quote.get("instrumentName", symbol), # SOURCE OF TRUTH for Name
                    "ltp": quote.get("lastPrice", 0),
                    "change": quote.get("change", 0),
                    "volume": quote.get("volume", 0),
                    "ohlc": f"O:{quote.get('open')} H:{quote.get('high')} L:{quote.get('low')}"
                })
            else:
                # Fallback if API fails for specific token
                stocks_data.append({
                    "id": db_id,
                    "symbol": symbol,
                    "name": "Loading...",
                    "ltp": "-",
                    "change": "-",
                    "volume": "-",
                    "ohlc": "-"
                })
                
    except Exception as e:
        print(f"Quote API Error: {e}")
        # Return DB data with placeholders
        for row in rows:
            stocks_data.append({"id": row[0], "symbol": row[1], "name": "API Error", "ltp":0})

    return jsonify(stocks_data)

@app.route('/api/add', methods=['POST'])
def add_stock():
    data = request.json
    symbol = data.get('symbol')
    token = data.get('token')
    
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Simple check to avoid duplicates
        c.execute("SELECT id FROM stocks WHERE exchange_token = ?", (token,))
        if not c.fetchone():
            c.execute("INSERT INTO stocks (watchlist_id, trading_symbol, exchange_token) VALUES (?, ?, ?)", 
                      (1, symbol, token)) # Hardcoded watchlist_id=1 for now
            conn.commit()
            return jsonify({"status": "success"})
        else:
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
