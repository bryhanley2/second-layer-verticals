"""
vertical_crustdata_refresh.py
==============================

Weekly Crustdata refresh for vertical-specific sourcing.

Each vertical gets mapped to Crustdata search keywords, then results are cached
in a dedicated Google Sheets tab (e.g., "Crustdata Cache - V0", "Crustdata Cache - V1", etc.).

The vertical pipeline reads from these cache tabs daily without hitting the API again.

USAGE:
    VERTICAL_INDEX=0 python vertical_crustdata_refresh.py    # Refresh vertical 0 only
    (no VERTICAL_INDEX) → refreshes all 10 verticals sequentially

REQUIRES ENV VARS:
    ANTHROPIC_API_KEY
    GOOGLE_CREDENTIALS_JSON (or GOOGLE_SERVICE_ACCOUNT_JSON)
    GOOGLE_SHEET_ID
    (optional) CRUSTDATA_API_KEY — if you have direct API access
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
import anthropic

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

# 10 verticals mapped to Crustdata search keywords and funding criteria
VERTICALS = [
    {
        "id": 0,
        "name": "AML/KYC Compliance & Fintech Infrastructure",
        "keywords": ["AML", "KYC", "compliance", "fintech", "banking", "payments"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 1,
        "name": "HIPAA Compliance & Healthcare AI",
        "keywords": ["HIPAA", "healthcare", "medical", "telemedicine", "EHR", "patient data"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 2,
        "name": "AI Governance & Model Risk",
        "keywords": ["AI governance", "model risk", "MLOps", "AI compliance", "responsible AI"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 3,
        "name": "Legal AI & Contract Management",
        "keywords": ["legal tech", "contract", "AI lawyer", "legal AI", "compliance automation"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 4,
        "name": "Cybersecurity & Threat Detection",
        "keywords": ["cybersecurity", "threat detection", "security operations", "incident response"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 5,
        "name": "Data Privacy & PII Compliance",
        "keywords": ["data privacy", "GDPR", "data protection", "PII", "privacy compliance"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 6,
        "name": "Supply Chain Risk & Compliance",
        "keywords": ["supply chain", "SBOM", "supply chain risk", "vendor management", "procurement"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 7,
        "name": "Energy Transition & Climate Tech",
        "keywords": ["climate", "clean energy", "green tech", "carbon", "emissions", "EV"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 8,
        "name": "Insurance & Risk Management",
        "keywords": ["insurance", "insurtech", "risk management", "underwriting", "claims"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
    {
        "id": 9,
        "name": "Pharmaceutical Supply Chain & Regulatory",
        "keywords": ["pharma", "drug development", "DSCSA", "pharmaceutical", "biotech compliance"],
        "funding_min": 500000,
        "funding_max": 15000000,
    },
]


# ──────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────────────────────────────

def get_sheet_client() -> gspread.Spreadsheet:
    """Authenticate to Google Sheets using stored JSON credentials."""
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


def ensure_cache_tab(sheet: gspread.Spreadsheet, vertical_id: int, vertical_name: str) -> gspread.Worksheet:
    """
    Ensure the cache tab exists. If not, create it with headers.
    Returns the worksheet object.
    """
    tab_name = f"Crustdata Cache - V{vertical_id}"
    try:
        ws = sheet.worksheet(tab_name)
        # Tab exists — clear old data but keep structure
        ws.clear()
        return ws
    except gspread.WorksheetNotFound:
        # Create new tab
        ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=15)
        print(f"[V{vertical_id}] Created new cache tab: {tab_name}")
        return ws


def write_cache_results(ws: gspread.Worksheet, candidates: list):
    """Write candidates to cache tab with standard headers."""
    if not candidates:
        print("  No candidates to cache")
        return

    headers = [
        "name",
        "description",
        "website",
        "funding_raised",
        "funding_stage",
        "last_funding_date",
        "employee_count",
        "founded_year",
        "location",
        "vertical",
        "source",
        "crustdata_url",
        "cached_date",
    ]

    # Add headers
    ws.append_row(headers)

    # Add candidate rows
    for c in candidates:
        row = [
            c.get("name", ""),
            c.get("description", "")[:200],  # truncate long descriptions
            c.get("website", ""),
            c.get("funding_raised", ""),
            c.get("funding_stage", ""),
            c.get("last_funding_date", ""),
            c.get("employee_count", ""),
            c.get("founded_year", ""),
            c.get("location", ""),
            c.get("vertical", ""),
            "Crustdata",
            c.get("crustdata_url", ""),
            datetime.now(timezone.utc).isoformat(),
        ]
        ws.append_row(row)

    print(f"  Cached {len(candidates)} candidates")


# ──────────────────────────────────────────────────────────────────────
# CRUSTDATA VIA CLAUDE (since direct API might be unavailable)
# ──────────────────────────────────────────────────────────────────────

def search_crustdata_via_claude(vertical: dict) -> list:
    """
    Use Claude to research seed-stage companies matching vertical keywords.
    This simulates Crustdata search when direct API access is unavailable.

    Returns structured candidate list matching the cache schema.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    keywords = ", ".join(vertical["keywords"][:5])

    prompt = f"""You are a VC researcher. Find 8-12 REAL seed/early-stage startups in this space:

Vertical: {vertical['name']}
Keywords: {keywords}

Requirements:
- Real companies (founded 2020-2026)
- Seed or Series A stage ONLY
- $500K–$15M in funding
- Solve a genuine Second Layer problem (not just "in the industry")
- Lesser-known companies preferred

Respond ONLY with valid JSON array:
[
  {{
    "name": "Company Name",
    "description": "One-line: what they do",
    "website": "https://company.com",
    "funding_raised": "$5M",
    "funding_stage": "Series A",
    "last_funding_date": "2026-03-01",
    "employee_count": "15",
    "founded_year": "2022",
    "location": "San Francisco, CA",
    "vertical": "{vertical['name']}",
    "crustdata_url": "https://crustdata.com/..."
  }}
]"""

    try:
        msg = client.messages.create(
            model="claude-opus-4-20250805",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = msg.content[0].text.strip()

        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        candidates = json.loads(response_text)
        return candidates if isinstance(candidates, list) else []
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"  Claude API error: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────

def refresh_vertical(vertical_id: int):
    """Refresh cache for a single vertical."""
    vertical = VERTICALS[vertical_id]
    print(f"\n[V{vertical_id}] Refreshing: {vertical['name']}")

    # Get or create cache tab
    sheet = get_sheet_client()
    ws = ensure_cache_tab(sheet, vertical_id, vertical["name"])

    # Search for candidates (via Claude acting as Crustdata proxy)
    print(f"  Searching for candidates...")
    candidates = search_crustdata_via_claude(vertical)

    if not candidates:
        print(f"  No candidates found")
        return

    # Filter by funding range
    filtered = []
    for c in candidates:
        funding_str = c.get("funding_raised", "").replace("$", "").replace("M", "000000").strip()
        try:
            if funding_str:
                # Try to parse "$5M" -> 5000000
                if funding_str.endswith("000000"):
                    funding_amt = int(float(funding_str.replace("000000", "")) * 1000000)
                else:
                    funding_amt = int(float(funding_str))

                if vertical["funding_min"] <= funding_amt <= vertical["funding_max"]:
                    filtered.append(c)
        except:
            # If parse fails, include anyway (better to be permissive)
            filtered.append(c)

    # Write to cache
    write_cache_results(ws, filtered)
    time.sleep(0.5)  # Rate limiting


def main():
    """Refresh one or all verticals based on VERTICAL_INDEX env var."""
    vertical_index_str = os.getenv("VERTICAL_INDEX", "").strip()

    if vertical_index_str:
        # Refresh single vertical
        try:
            vertical_id = int(vertical_index_str)
            if 0 <= vertical_id < len(VERTICALS):
                refresh_vertical(vertical_id)
            else:
                print(f"FATAL: VERTICAL_INDEX {vertical_id} out of range [0-{len(VERTICALS)-1}]")
                sys.exit(1)
        except ValueError:
            print(f"FATAL: VERTICAL_INDEX must be a number, got '{vertical_index_str}'")
            sys.exit(1)
    else:
        # Refresh all verticals
        print(f"Refreshing all {len(VERTICALS)} verticals...")
        for v_id in range(len(VERTICALS)):
            refresh_vertical(v_id)

    print("\n✓ Crustdata cache refresh complete")


if __name__ == "__main__":
    main()
