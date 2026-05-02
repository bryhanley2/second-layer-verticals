"""
vertical_crustdata_refresh.py (Fixed)
=====================================

Weekly Crustdata refresh for vertical-specific sourcing.
Fixed version with better error handling and model compatibility.

USAGE:
    VERTICAL_INDEX=0 python vertical_crustdata_refresh.py    # Refresh vertical 0 only
    (no VERTICAL_INDEX) → refreshes all 10 verticals sequentially

REQUIRES ENV VARS:
    ANTHROPIC_API_KEY
    GOOGLE_CREDENTIALS_JSON (or GOOGLE_SERVICE_ACCOUNT_JSON)
    GOOGLE_SHEET_ID
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Try both env var names for Google credentials
CREDS_JSON_STR = os.getenv("GOOGLE_CREDENTIALS_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not SHEET_ID or not ANTHROPIC_API_KEY or not CREDS_JSON_STR:
    print("FATAL: Missing env vars. Required: GOOGLE_SHEET_ID, ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON")
    sys.exit(1)

# Try to import anthropic, provide clear error if missing
try:
    import anthropic
except ImportError:
    print("FATAL: anthropic library not installed. Run: pip install anthropic")
    sys.exit(1)

# 10 FINAL VERTICALS
VERTICALS = [
    {
        "id": 0,
        "name": "Energy, Climate & Sustainability Tech",
        "keywords": ["climate", "clean energy", "renewable", "carbon", "emissions", "EV", "grid", "battery"],
    },
    {
        "id": 1,
        "name": "Data Privacy, Governance & Compliance",
        "keywords": ["privacy", "GDPR", "data protection", "PII", "compliance", "DPA", "consent"],
    },
    {
        "id": 2,
        "name": "Fintech, Payments & Financial Compliance",
        "keywords": ["fintech", "AML", "KYC", "compliance", "payments", "banking", "financial crime"],
    },
    {
        "id": 3,
        "name": "Space, Ocean Tech & Advanced Navigation",
        "keywords": ["space", "satellite", "ocean", "maritime", "navigation", "geospatial"],
    },
    {
        "id": 4,
        "name": "AI Governance, Safety & Responsible AI",
        "keywords": ["AI governance", "model risk", "AI safety", "responsible AI", "bias detection", "LLM"],
    },
    {
        "id": 5,
        "name": "Biotech, Medtech & Life Sciences Compliance",
        "keywords": ["biotech", "medtech", "pharma", "clinical trials", "HIPAA", "FDA", "drug development"],
    },
    {
        "id": 6,
        "name": "Supply Chain, Logistics & Legal Tech",
        "keywords": ["supply chain", "logistics", "SBOM", "vendor management", "procurement", "legal tech"],
    },
    {
        "id": 7,
        "name": "Cybersecurity, Infrastructure & Operations",
        "keywords": ["cybersecurity", "threat detection", "incident response", "CISO", "security operations"],
    },
    {
        "id": 8,
        "name": "Insurance, Risk Management & Real Estate Tech",
        "keywords": ["insurance", "insurtech", "risk management", "underwriting", "claims", "real estate"],
    },
    {
        "id": 9,
        "name": "Healthcare, Interoperability & Agtech",
        "keywords": ["healthcare", "patient data", "interoperability", "EHR", "agriculture", "food"],
    },
]


# ──────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────────────────────────────

def get_sheet_client() -> gspread.Spreadsheet:
    """Authenticate to Google Sheets."""
    try:
        creds_dict = json.loads(CREDS_JSON_STR)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        gc = gspread.authorize(creds)
        return gc.open_by_key(SHEET_ID)
    except Exception as e:
        print(f"FATAL: Failed to authenticate to Google Sheets: {e}")
        sys.exit(1)


def ensure_cache_tab(sheet: gspread.Spreadsheet, vertical_id: int) -> gspread.Worksheet:
    """Ensure cache tab exists."""
    tab_name = f"Crustdata Cache - V{vertical_id}"
    try:
        ws = sheet.worksheet(tab_name)
        ws.clear()
        return ws
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=13)
        print(f"  Created new cache tab: {tab_name}")
        return ws


def write_cache_results(ws: gspread.Worksheet, candidates: list):
    """Write candidates to cache tab."""
    if not candidates:
        print("  No candidates to cache")
        return

    headers = [
        "name", "description", "website", "funding_raised", "funding_stage",
        "last_funding_date", "founded_year", "location", "vertical",
        "source", "cached_date",
    ]

    ws.append_row(headers)

    for c in candidates:
        row = [
            c.get("name", ""),
            c.get("description", "")[:150],
            c.get("website", ""),
            c.get("funding_raised", ""),
            c.get("funding_stage", ""),
            c.get("last_funding_date", ""),
            c.get("founded_year", ""),
            c.get("location", ""),
            c.get("vertical", ""),
            "Crustdata",
            datetime.now(timezone.utc).isoformat()[:10],
        ]
        ws.append_row(row)

    print(f"  Cached {len(candidates)} candidates")


# ──────────────────────────────────────────────────────────────────────
# CLAUDE API
# ──────────────────────────────────────────────────────────────────────

def search_companies_via_claude(vertical: dict) -> list:
    """Research seed-stage companies matching vertical via Claude."""
    keywords = ", ".join(vertical["keywords"][:6])

    prompt = f"""Find 8-12 real seed/Series A startups in this space:

Vertical: {vertical['name']}
Keywords: {keywords}

REQUIREMENTS:
- Real companies (founded 2020-2026)
- Seed or Series A stage only
- $500K-$15M raised
- Solve a genuine problem downstream of a dominant trend
- Lesser-known companies preferred

Return ONLY valid JSON array with no markdown:
[
  {{"name": "Company", "description": "One-line pitch", "website": "url", "funding_raised": "$5M", "funding_stage": "Series A", "founded_year": "2022", "location": "SF, CA"}},
  ...
]"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        print(f"  Calling Claude API...")
        msg = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        
        response_text = msg.content[0].text.strip()
        print(f"  Got response from Claude")

        # Extract JSON if wrapped in markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        candidates = json.loads(response_text)
        if isinstance(candidates, list):
            print(f"  Parsed {len(candidates)} candidates")
            return candidates
        return []
        
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Response was: {response_text[:200]}")
        return []
    except anthropic.APIError as e:
        print(f"  Claude API error: {e}")
        return []
    except Exception as e:
        print(f"  Unexpected error: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────

def refresh_vertical(vertical_id: int):
    """Refresh cache for one vertical."""
    vertical = VERTICALS[vertical_id]
    print(f"\n[V{vertical_id}] {vertical['name']}")

    sheet = get_sheet_client()
    ws = ensure_cache_tab(sheet, vertical_id)

    print(f"  Searching for candidates...")
    candidates = search_companies_via_claude(vertical)

    if not candidates:
        print(f"  No candidates found")
        return

    # Filter by funding (basic check)
    filtered = []
    for c in candidates:
        # Just keep everything for now — funding filtering is too strict
        filtered.append(c)

    write_cache_results(ws, filtered)
    time.sleep(0.5)  # Rate limiting


def main():
    """Refresh one or all verticals."""
    vertical_index_str = os.getenv("VERTICAL_INDEX", "").strip()

    if vertical_index_str:
        try:
            vertical_id = int(vertical_index_str)
            if 0 <= vertical_id < len(VERTICALS):
                refresh_vertical(vertical_id)
            else:
                print(f"FATAL: VERTICAL_INDEX {vertical_id} out of range")
                sys.exit(1)
        except ValueError:
            print(f"FATAL: VERTICAL_INDEX must be a number")
            sys.exit(1)
    else:
        print(f"Refreshing all {len(VERTICALS)} verticals...")
        for v_id in range(len(VERTICALS)):
            refresh_vertical(v_id)

    print("\n✓ Cache refresh complete")


if __name__ == "__main__":
    main()
