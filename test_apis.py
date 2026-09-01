import os
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

# Test 2: Google Sheets
print("\n[2] Testing Google Sheets...")
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
