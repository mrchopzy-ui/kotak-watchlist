import csv
import requests

OUTPUT_FILE = "company_master.csv"

URL = "https://www.nseindia.com/content/equities/EQUITY_L.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/csv",
    "Referer": "https://www.nseindia.com"
}

def main():
    print("📥 Downloading NSE EQUITY_L.csv (official equity master)...")

    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()

    lines = r.text.splitlines()
    reader = csv.DictReader(lines)

    companies = {}

    for row in reader:
        if row.get("SERIES") == "EQ":
            symbol = row["SYMBOL"].strip().upper()
            name = row["NAME OF COMPANY"].strip().title()
            companies[symbol] = name

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "legal_name"])
        for s in sorted(companies):
            w.writerow([s, companies[s]])

    print(f"✅ Done. Saved {len(companies)} companies to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
