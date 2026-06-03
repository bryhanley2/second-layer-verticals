import os
import requests
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import json

print("="*60)
print("API CREDENTIAL TEST")
print("="*60)

# Test 1: Anthropic
print("\n[1] Testing Anthropic API...")
try:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say 'API works'"}]
    )
    print(f"✅ Anthropic OK: {resp.content[0].text}")
except Exception as e:
    print(f"❌ Anthropic FAILED: {e}")

# Test 2: Crustdata
print("\n[2] Testing Crustdata API...")
try:
    headers = {"Authorization": f"Token {os.environ['CRUSTDATA_API_KEY']}", "Content-Type": "application/json"}
    r = requests.post(
        "https://api.crustdata.com/screener/company/search",
        headers=headers,
        json={"filters": [{"filter_type": "INDUSTRY", "type": "in", "value": ["Software"]}], "page": 1},
        timeout=30,
    )
    print(f"✅ Crustdata Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Got {len(data.get('companies', []))} companies")
    else:
        print(f"   Response: {r.text[:300]}")
except Exception as e:
    print(f"❌ Crustdata FAILED: {e}")

# Test 3: Google Sheets
print("\n[3] Testing Google Sheets...")
try:
    creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    print(f"✅ Google Sheets OK: opened '{sheet.title}'")
except Exception as e:
    print(f"❌ Google Sheets FAILED: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
