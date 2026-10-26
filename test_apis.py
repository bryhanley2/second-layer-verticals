import os
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import json

# Test against the exact model the pipeline uses. Falls back to a literal if
# pipeline_utils can't be imported so the diagnostic still runs standalone.
try:
    from pipeline_utils import MODEL
except Exception:
    MODEL = os.environ.get("PIPELINE_MODEL") or "claude-sonnet-5-5"

print("="*60)
print("API CREDENTIAL TEST")
print("="*60)

# Test 1: Anthropic
print(f"\n[1] Testing Anthropic API (model={MODEL})...")
try:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,  # headroom: Sonnet 5/5.5 think by default
        messages=[{"role": "user", "content": "Say 'API works'"}]
    )
    _txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    print(f"✅ Anthropic OK: {_txt}")
except Exception as e:
    print(f"❌ Anthropic FAILED: {e}")

# Test 1b: web search tool (the pipeline's sourcing + funding verification use it)
print(f"\n[1b] Testing web search tool (model={MODEL}, ~1 search, about a cent)...")
try:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 1}],
        messages=[{"role": "user", "content": "Use web search once: what is the URL of the Anthropic homepage? Answer in one line."}],
    )
    n_search = sum(1 for b in resp.content if getattr(b, "type", "") == "server_tool_use")
    _txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    print(f"✅ Web search OK ({n_search} search call(s)): {_txt[:120]}")
except Exception as e:
    print(f"❌ Web search FAILED: {e}")

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
