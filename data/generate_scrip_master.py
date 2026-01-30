import csv
import requests
import pyotp
import json

ACCESS_TOKEN = "5299a2a1-21fa-42e2-b9b3-b63be76a2553"
MOBILE = "+919551441970"
USER_ID = "YALD5"
MPIN = "124689"
TOTP_SECRET = "YOYAZGFRWAU2FXZM2XA43RVQVU"

print("🔐 Generating TOTP...")
totp = pyotp.TOTP(TOTP_SECRET).now()
print("TOTP:", totp)

print("➡️ Step 1: tradeApiLogin")
r1 = requests.post(
    "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
    headers={
        "Authorization": ACCESS_TOKEN,
        "neo-fin-key": "neotradeapi",
        "Content-Type": "application/json"
    },
    json={
        "mobileNumber": MOBILE,
        "ucc": USER_ID,
        "totp": totp
    },
    timeout=10
)

print("Login response:")
print(json.dumps(r1.json(), indent=2))

if "data" not in r1.json():
    raise RuntimeError("❌ tradeApiLogin failed. Fix credentials/TOTP.")

view_sid = r1.json()["data"]["sid"]
view_token = r1.json()["data"]["token"]

print("➡️ Step 2: tradeApiValidate")
r2 = requests.post(
    "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
    headers={
        "Authorization": ACCESS_TOKEN,
        "neo-fin-key": "neotradeapi",
        "sid": view_sid,
        "Auth": view_token,
        "Content-Type": "application/json"
    },
    json={"mpin": MPIN},
    timeout=10
)

print("Validate response:")
print(json.dumps(r2.json(), indent=2))

if "data" not in r2.json():
    raise RuntimeError("❌ MPIN validation failed.")

base = r2.json()["data"]["baseUrl"]

print("➡️ Fetching scrip master paths")
paths = requests.get(
    f"{base}/script-details/1.0/masterscrip/file-paths",
    headers={"Authorization": ACCESS_TOKEN},
    timeout=10
).json()

nse_csv = [x for x in paths["data"]["filesPaths"] if "nse_cm" in x][0]
print("Downloading:", nse_csv)

rows = csv.DictReader(requests.get(nse_csv).text.splitlines())

print("💾 Writing CSV...")
with open("nse_eq_scrip_master.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["exchange_token", "trading_symbol", "company_name"])
    count = 0
    for r in rows:
        if r.get("series") == "EQ":
            w.writerow([r["pSymbol"], r["pTrdSymbol"], r.get("name", "")])
            count += 1

print(f"✅ Done. Saved {count} NSE EQ stocks")
