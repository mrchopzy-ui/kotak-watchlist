import csv
import requests
import pyotp
import os

ACCESS_TOKEN = os.getenv("KOTAK_ACCESS_TOKEN")
MOBILE = os.getenv("KOTAK_MOBILE")
USER_ID = os.getenv("KOTAK_USER_ID")
MPIN = os.getenv("KOTAK_MPIN")
TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET")

print("🔐 Generating TOTP...")
totp = pyotp.TOTP(TOTP_SECRET).now()

# ---------------- LOGIN ----------------
print("➡️ tradeApiLogin")
r1 = requests.post(
    "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
    headers={
        "Authorization": ACCESS_TOKEN,
        "neo-fin-key": "neotradeapi"
    },
    json={
        "mobileNumber": MOBILE,
        "ucc": USER_ID,
        "totp": totp
    }
).json()

print("➡️ tradeApiValidate")
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

base = r2["data"]["baseUrl"]

# ---------------- FETCH MASTER ----------------
print("📂 Fetching scrip master paths...")
paths = requests.get(
    f"{base}/script-details/1.0/masterscrip/file-paths",
    headers={"Authorization": ACCESS_TOKEN}
).json()

csv_url = [p for p in paths["data"]["filesPaths"] if "nse_cm" in p.lower()][0]
print("⬇️ Downloading:", csv_url)

text = requests.get(csv_url).text.splitlines()
reader = csv.DictReader(text)

print("🧾 CSV columns detected:")
print(reader.fieldnames)

# ---------------- WRITE EQ MASTER ----------------
count = 0
with open("nse_eq_scrip_master.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["trading_symbol", "exchange_token"])

    for r in reader:
        ts = r.get("pTrdSymbol", "")

        # ✅ ONLY NSE CASH EQUITIES
        if ts.endswith("-EQ"):
            writer.writerow([
                ts,
                r.get("pSymbol")
            ])
            count += 1

print(f"✅ Saved nse_eq_scrip_master.csv with {count} NSE EQ stocks")
