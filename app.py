import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, jsonify
from ks_api_client import ks_api

app = Flask(__name__)

# --- CONFIGURATION ---
DB_PATH = 'watchlists.db'
CSV_PATH = 'data/nse_eq_scrip_master.csv'

# --- DATABASE HELPERS ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS watchlists 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS stocks 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         watchlist_id INTEGER, 
                         symbol TEXT, 
                         token TEXT,
                         company_name TEXT,
                         FOREIGN KEY(watchlist_id) REFERENCES watchlists(id))''')
        try:
            conn.execute("INSERT INTO watchlists (name) VALUES ('Main')")
        except sqlite3.IntegrityError:
            pass

init_db()

# --- UTILS ---
def format_volume(vol):
    try:
        vol = float(vol)
        if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
        if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
        if vol >= 1_000: return f"{vol/1_000:.2f}K"
        return str(vol)
    except:
        return "0"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search_stocks():
    query = request.args.get('q', '').upper()
    if not query: return jsonify([])
    try:
        df = pd.read_csv(CSV_PATH)
        results = df[df['symbol'].str.contains(query, na=False)].head(10)
        return jsonify(results.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlists', methods=['GET', 'POST'])
def manage_watchlists():
    with sqlite3.connect(DB_PATH) as conn:
        if request.method == 'POST':
            name = request.json.get('name')
            conn.execute("INSERT INTO watchlists (name) VALUES (?)", (name,))
            return jsonify({"status": "success"})
        
        cur = conn.execute("SELECT * FROM watchlists")
        return jsonify([{"id": r[0], "name": r[1]} for r in cur.fetchall()])

@app.route('/api/watchlists/<int:wid>', methods=['DELETE', 'PUT'])
def modify_watchlist(wid):
    with sqlite3.connect(DB_PATH) as conn:
        if request.method == 'DELETE':
            conn.execute("DELETE FROM stocks WHERE watchlist_id = ?", (wid,))
            conn.execute("DELETE FROM watchlists WHERE id = ?", (wid,))
        elif request.method == 'PUT':
            new_name = request.json.get('name')
            conn.execute("UPDATE watchlists SET name = ? WHERE id = ?", (new_name, wid))
        return jsonify({"status": "success"})

@app.route('/api/stocks', methods=['GET', 'POST'])
def manage_stocks():
    with sqlite3.connect(DB_PATH) as conn:
        if request.method == 'POST':
            data = request.json
            conn.execute("INSERT INTO stocks (watchlist_id, symbol, token, company_name) VALUES (?, ?, ?, ?)",
                         (data['watchlist_id'], data['symbol'], data['token'], data['company_name']))
            return jsonify({"status": "success"})
        
        wid = request.args.get('watchlist_id')
        cur = conn.execute("SELECT id, symbol, token, company_name FROM stocks WHERE watchlist_id = ?", (wid,))
        stocks = [{"id": r[0], "symbol": r[1], "token": r[2], "company": r[3]} for r in cur.fetchall()]
        return jsonify(stocks)

@app.route('/api/stocks/<int:sid>', methods=['DELETE'])
def delete_stock(sid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM stocks WHERE id = ?", (sid,))
        return jsonify({"status": "success"})

@app.route('/api/quotes')
def get_quotes():
    tokens = request.args.get('tokens', '').split(',')
    if not tokens or tokens == ['']: return jsonify({})
    
    # Simulate Kotak API responses for development/production
    # In live: call client.quote(instrument_token=token)
    results = {}
    for token in tokens:
        results[token] = {
            "ltp": 2500.50, "change": 1.25, "vol": "1.5M",
            "open": 2480.00, "high": 2510.00, "low": 2470.00, "close": 2475.00
        }
    return jsonify(results)

@app.route('/api/market_indices')
def get_market_indices():
    indices = [
        {"name": "NIFTY 50", "price": "22,123.45", "change": "+0.45%"},
        {"name": "BANK NIFTY", "price": "46,890.10", "change": "-0.12%"}
    ]
    return jsonify(indices)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
