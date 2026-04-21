"""
Vertical Crustdata Refresh
===========================
On-demand refresh for a specific vertical. Takes vertical index (0-9) as input,
pulls seed-stage companies matching that vertical's sector keywords, writes
to a per-vertical cache tab.

Usage:
    VERTICAL_INDEX=0 python vertical_crustdata_refresh.py   # Space & Defence
    VERTICAL_INDEX=3 python vertical_crustdata_refresh.py   # Healthcare

One API credit per run. Runs on-demand via GitHub Actions manual trigger.
"""

import os
import json
import sys
import requests
from datetime import datetime, timezone
from pipeline_utils import get_sheet_client, SHEET_ID
from vertical_sources import get_vertical, get_vertical_name

import gspread

CRUSTDATA_ENDPOINT = "https://api.crustdata.com/screener/screen/"

MAX_TOTAL_FUNDING_USD = 15_000_000
MIN_HEADCOUNT = 1
MAX_HEADCOUNT = 30
MAX_DAYS_SINCE_LAST_ROUND = 730
MAX_COMPANY_AGE_DAYS = 5 * 365


def build_vertical_query(keywords: list) -> dict:
    return {
        "conditions": [
            {"column": "headcount", "type": "in_between",
             "value": [MIN_HEADCOUNT, MAX_HEADCOUNT]},
            {"column": "total_funding_usd", "type": "<=",
             "value": MAX_TOTAL_FUNDING_USD},
            {"column": "days_since_last_funding_round", "type": "<=",
             "value": MAX_DAYS_SINCE_LAST_ROUND},
            {"column": "hq_country", "type": "in",
             "value": ["United States"]},
            {"column": "days_since_founded", "type": "<=",
             "value": MAX_COMPANY_AGE_DAYS},
            {"column": "industry_keywords", "type": "any_of",
             "value": keywords},
        ],
        "page": 1,
        "per_page": 100,
    }


def call_crustdata(query: dict) -> list:
    api_key = os.environ.get("CRUSTDATA_API_KEY")
    if not api_key:
        raise RuntimeError("CRUSTDATA_API_KEY not set")
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    print(f"Calling Crustdata /screener/screen/ ...")
    response = requests.post(CRUSTDATA_ENDPOINT, headers=headers, json=query, timeout=60)
    if response.status_code != 200:
        print(f"API error {response.status_code}: {response.text[:500]}")
        return []
    data = response.json()
    return data.get("results", data.get("data", []))


def normalise(raw: dict) -> dict:
    def safe_get(d, *keys, default=""):
        for key in keys:
            if isinstance(d, dict) and key in d and d[key] is not None:
                d = d[key]
            else:
                return default
        return d

    return {
        "name": safe_get(raw, "company_name", default=safe_get(raw, "name")),
        "website": safe_get(raw, "website", default=safe_get(raw, "domain")),
        "hq_city": safe_get(raw, "hq_city", default=""),
        "hq_country": safe_get(raw, "hq_country", default=""),
        "founded_date": safe_get(raw, "founded_date", default=safe_get(raw, "year_founded")),
        "headcount": safe_get(raw, "headcount", default=0),
        "total_funding_usd": safe_get(raw, "total_funding_usd", default=0),
        "last_funding_round": safe_get(raw, "last_funding_round", default=""),
        "last_funding_date": safe_get(raw, "last_funding_date", default=""),
        "last_funding_amount_usd": safe_get(raw, "last_funding_amount_usd", default=0),
        "industry": safe_get(raw, "industry", default=""),
        "description": safe_get(raw, "short_description", default=safe_get(raw, "description", default="")),
        "linkedin_url": safe_get(raw, "linkedin_url", default=""),
    }


def write_cache(companies: list, vertical_idx: int, vertical_name: str):
    cache_tab = f"Crustdata Cache - V{vertical_idx}"
    client = get_sheet_client()
    sheet = client.open_by_key(SHEET_ID)
    try:
        tab = sheet.worksheet(cache_tab)
    except gspread.WorksheetNotFound:
        tab = sheet.add_worksheet(title=cache_tab, rows=500, cols=16)

    tab.clear()
    headers = [
        "refresh_date", "vertical", "name", "website", "hq_city", "hq_country",
        "founded_date", "headcount", "total_funding_usd",
        "last_funding_round", "last_funding_date", "last_funding_amount_usd",
        "industry", "description", "linkedin_url",
    ]
    tab.append_row(headers)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for c in companies:
        rows.append([
            now, vertical_name, c["name"], c["website"],
            c["hq_city"], c["hq_country"],
            str(c["founded_date"]), c["headcount"], c["total_funding_usd"],
            c["last_funding_round"], str(c["last_funding_date"]),
            c["last_funding_amount_usd"], c["industry"],
            str(c["description"])[:500], c["linkedin_url"],
        ])
    if rows:
        tab.append_rows(rows)
        print(f"Wrote {len(rows)} rows to '{cache_tab}'")


def main():
    try:
        idx = int(os.environ.get("VERTICAL_INDEX", "0"))
    except ValueError:
        raise RuntimeError("VERTICAL_INDEX must be an integer 0-9")

    if idx < 0 or idx > 9:
        raise RuntimeError(f"VERTICAL_INDEX={idx} out of range")

    vertical = get_vertical(idx)
    name = vertical["name"]
    keywords = vertical["crustdata_keywords"]

    print(f"Vertical refresh — {idx}: {name}")
    print(f"Keywords: {keywords}")

    query = build_vertical_query(keywords)
    raw = call_crustdata(query)
    print(f"Returned {len(raw)} companies")

    if not raw:
        print("No results, cache not updated.")
        return

    normalised = [normalise(c) for c in raw]
    write_cache(normalised, idx, name)
    print("Refresh complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
