from flask import Flask

app = Flask(__name__)

import csv
import requests

URL = "https://www.nseindia.com/api/equity-master"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive"
}

print("📥 Downloading NSE equity master...")

session = requests.Session()
session.headers.update(HEADERS)

# First request to set cookies
session.get("https://www.nseindia.com", timeout=10)

# Actual data request
r = session.get(URL, timeout=10)
r.raise_for_status()

data = r.json()

count = 0
with open("company_master.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["SYMBOL", "NAME OF COMPANY"])

    for row in data.get("data", []):
        symbol = row.get("symbol")
        name = row.get("companyName")

        if symbol and name:
            writer.writerow([symbol.upper(), name.strip()])
            count += 1

print(f"✅ Saved company_master.csv with {count} companies")
