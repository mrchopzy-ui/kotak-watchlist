import sqlite3
import os

DB_PATH = "watchlists.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER,
    symbol TEXT,
    exchange_token TEXT,
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id)
)
""")

# create default watchlist if empty
cur.execute("SELECT COUNT(*) FROM watchlists")
if cur.fetchone()[0] == 0:
    cur.execute("INSERT INTO watchlists (name) VALUES (?)", ("Watchlist 1",))

conn.commit()
conn.close()

print("✅ watchlists.db created successfully")
