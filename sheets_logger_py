"""
sheets_logger.py — Appends daily pipeline results to a Google Sheet.

Setup (one-time, ~10 minutes):
1. Go to console.cloud.google.com
2. Create a new project (or use existing)
3. Enable the Google Sheets API and Google Drive API
4. Create a Service Account → download the JSON key file
5. Share your Google Sheet with the service account email (Editor access)
6. Add the JSON key contents as a GitHub Secret named GOOGLE_SERVICE_ACCOUNT_JSON
7. Add your Sheet ID as a GitHub Secret named GOOGLE_SHEET_ID
"""

import os
import json
import datetime
import requests

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS — order matches the sheet header row
# ─────────────────────────────────────────────────────────────────────────────
COLUMNS = [
    "Date",
    "Company",
    "Stage",
    "Raise",
    "Vertical",
    "Source",
    "Second Layer Logic",
    "What They Do",
    "Second Layer Aligned",
    # Factor scores
    "1A Founder-Mkt Fit",
    "1B Tech Execution",
    "1C Commitment",
    "2A Early PMF",
    "3A TAM",
    "3B Timing",
    "5 Traction Qual",
    "6 Cap Efficiency",
    "7 Investor Signal",
    # Summary
    "Weighted Score",
    "Score %",
    "Decision",
    "Key Strength",
    "Key Weakness",
]

# Columns for the "Founder Pipeline" tab — must match sheet exactly
# A          B               C        D          E                    F         G          H       I       J                  K             L                 M                N
FOUNDER_COLUMNS = [
    "Company", "Founder Name", "Title", "Vertical", "Second Layer Logic", "Score %", "Decision", "Stage", "Raise", "Source / Session", "Date Added", "Outreach Status", "Last Contacted", "Notes",
]

SCORE_KEYS = ["1A","1B","1C","2A","3A","3B","5","6","7"]


def _get_access_token(service_account_json: str) -> str:
    """
    Gets a short-lived OAuth2 access token from a Google Service Account JSON key.
    Uses the google-auth library if available, otherwise falls back to manual JWT.
    """
    try:
        import google.auth
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        info = json.loads(service_account_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        creds.refresh(Request())
        return creds.token

    except ImportError:
        # Manual JWT approach if google-auth not installed
        import base64
        import hmac
        import hashlib
        import time
        import struct

        info   = json.loads(service_account_json)
        now    = int(time.time())
        claims = {
            "iss":   info["client_email"],
            "scope": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive",
            "aud":   "https://oauth2.googleapis.com/token",
            "exp":   now + 3600,
            "iat":   now,
        }

        def b64(data):
            if isinstance(data, str):
                data = data.encode()
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header    = b64(json.dumps({"alg": "RS256", "typ": "JWT"}))
        payload   = b64(json.dumps(claims))
        sign_input = f"{header}.{payload}"

        # Sign with RSA private key
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        private_key = serialization.load_pem_private_key(
            info["private_key"].encode(),
            password=None,
            backend=default_backend(),
        )
        signature = private_key.sign(sign_input.encode(), padding.PKCS1v15(), hashes.SHA256())
        jwt = f"{sign_input}.{b64(signature)}"

        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt,
            },
        )
        return resp.json()["access_token"]


def company_to_row(result: dict, date_str: str) -> list:
    """Converts a scored company dict into a flat row for the Pipeline tab."""
    scores = result.get("scores", {})
    return [
        date_str,
        result.get("company_name", ""),
        result.get("stage", ""),
        result.get("raise", ""),
        result.get("vertical", ""),
        result.get("source", ""),
        result.get("second_layer_logic", ""),
        result.get("what_they_do", ""),
        "Yes" if result.get("second_layer_alignment") else "No",
        scores.get("1A", ""),
        scores.get("1B", ""),
        scores.get("1C", ""),
        scores.get("2A", ""),
        scores.get("3A", ""),
        scores.get("3B", ""),
        scores.get("5", ""),
        scores.get("6", ""),
        scores.get("7", ""),
        result.get("weighted_score", ""),
        result.get("score_pct", ""),
        result.get("decision", ""),
        result.get("key_strength", ""),
        result.get("key_weakness", ""),
    ]


def founder_to_row(result: dict, date_str: str) -> list:
    """Converts a scored company dict into a flat row for the Founder Pipeline tab.
    Column order matches the existing sheet exactly:
    Company | Founder Name | Title | Vertical | Second Layer Logic |
    Score % | Decision | Stage | Raise | Source / Session |
    Date Added | Outreach Status | Last Contacted | Notes
    """
    founder = result.get("founder", {})
    return [
        result.get("company_name", ""),           # A: Company
        founder.get("founder_name", ""),           # B: Founder Name
        founder.get("founder_title", ""),          # C: Title
        result.get("vertical", ""),                # D: Vertical
        result.get("second_layer_logic", ""),      # E: Second Layer Logic
        result.get("score_pct", ""),               # F: Score %
        result.get("decision", ""),                # G: Decision
        result.get("stage", ""),                   # H: Stage
        result.get("raise", ""),                   # I: Raise
        result.get("source", ""),                  # J: Source / Session
        date_str,                                  # K: Date Added
        "Not Started",                             # L: Outreach Status
        "",                                        # M: Last Contacted
        "",                                        # N: Notes
    ]



def get_previously_seen_companies() -> set:
    """
    Reads the Company column from the Pipeline sheet and returns
    a set of lowercase company names already evaluated.
    Returns empty set if sheet not configured or empty.
    """
    sa_json  = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")

    print(f"DEBUG get_previously_seen: sa_json length={len(sa_json)}, sheet_id='{sheet_id}'")
    if not sa_json or not sheet_id:
        return set()

    try:
        token = _get_access_token(sa_json)
        url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
               f"/values/Pipeline!B2:B10000")
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        rows = resp.json().get("values", [])
        seen = {row[0].lower().strip() for row in rows if row}
        print(f"Loaded {len(seen)} previously seen companies from sheet")
        return seen
    except Exception as e:
        print(f"Could not load previous companies: {e}")
        return set()


def _ensure_tab(sheet_meta_url: str, token: str, sheet_names: list, tab_name: str):
    """Creates a tab if it doesn't already exist."""
    if tab_name not in sheet_names:
        requests.post(
            f"{sheet_meta_url}:batchUpdate",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        )
        print(f"Created '{tab_name}' tab")


def _ensure_header(sheet_id: str, token: str, tab: str, headers: list):
    """Writes header row to a tab if it's empty."""
    url  = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{tab}!A1:Z1"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    existing = resp.json().get("values", [])
    if not existing or existing[0][0] != headers[0]:
        write_url = f"{url}?valueInputOption=RAW"
        requests.put(
            write_url,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"values": [headers]},
        )
        print(f"Header row written to '{tab}'")


def _get_last_row(sheet_id: str, token: str, tab: str) -> int:
    """
    Finds the true last occupied row in column A of a tab by reading all values.
    Returns the row number (1-indexed) of the last non-empty cell in column A.
    Falls back to row 1 if the tab is empty.
    """
    url  = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            f"/values/{tab}!A:A")
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    values = resp.json().get("values", [])
    # Walk backwards to find the last non-empty cell
    for i in range(len(values) - 1, -1, -1):
        if values[i] and str(values[i][0]).strip():
            return i + 1  # 1-indexed
    return 0


def _append_rows(sheet_id: str, token: str, tab: str, rows: list):
    """
    Writes rows directly after the last occupied row in the tab.
    Explicitly finds the last row rather than relying on the Sheets API append
    logic, which can misfire when there are blank rows or formatting sections
    below the data (e.g. OUTREACH STATUS KEY blocks).
    """
    last_row   = _get_last_row(sheet_id, token, tab)
    start_row  = last_row + 1
    range_ref  = f"{tab}!A{start_row}"
    url        = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
                  f"/values/{range_ref}?valueInputOption=RAW")
    resp = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"values": rows},
    )
    if resp.status_code == 200:
        updated = resp.json().get("updatedRows", len(rows))
        print(f"  {updated} rows written to '{tab}' starting at row {start_row}")
    else:
        print(f"  Sheets API error on '{tab}': {resp.status_code} — {resp.text[:200]}")


def _rgb(hex_color: str) -> dict:
    """Converts a hex color string to a Sheets API RGB object (0-1 scale)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def _get_sheet_id(sheet_meta_url: str, token: str, tab_name: str) -> int:
    """Returns the numeric sheetId for a named tab."""
    meta = requests.get(
        sheet_meta_url,
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            return s["properties"]["sheetId"]
    return 0


def _format_founder_rows(sheet_id: str, sheet_meta_url: str, token: str,
                          start_row: int, num_rows: int, rows: list):
    """
    Applies formatting to newly written Founder Pipeline rows to match
    the existing CRM styling:
      - Alternating row backgrounds (white / light grey)
      - Bold font for Founder Name (col B)
      - Decision column (col G) colour-coded by rating
      - Arial font, size 10, vertically centered, text wrap on all cells
      - Thin border on all cells
    Row indices are 0-based in the Sheets API (start_row - 1).
    """
    tab_sheet_id = _get_sheet_id(sheet_meta_url, token, "Founder Pipeline")

    # Colour map for Decision column (col index 6 = G)
    DECISION_COLORS = {
        "strong yes": {"bg": "D1FAE5", "fg": "065F46"},
        "yes":        {"bg": "EAF3DE", "fg": "3B6D11"},
        "deep dive":  {"bg": "FFF8E1", "fg": "854F0B"},
        "pass":       {"bg": "FCEBEB", "fg": "A32D2D"},
    }

    ROW_BG_EVEN = "FFFFFF"  # white
    ROW_BG_ODD  = "F8FAFC"  # light grey

    border_style = {
        "style": "SOLID",
        "width": 1,
        "color": _rgb("D1D9E6"),
    }

    def cell_border():
        return {k: border_style for k in ("top", "bottom", "left", "right")}

    batch_requests = []

    for i, row_data in enumerate(rows):
        row_idx = (start_row - 1) + i   # 0-based
        is_even = ((start_row + i) % 2 == 0)
        row_bg  = ROW_BG_EVEN if is_even else ROW_BG_ODD

        # ── Base row formatting — all 14 columns ─────────────────────────────
        batch_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId":          tab_sheet_id,
                    "startRowIndex":    row_idx,
                    "endRowIndex":      row_idx + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex":   14,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(row_bg),
                        "textFormat": {
                            "fontFamily": "Arial",
                            "fontSize":   10,
                            "bold":       False,
                            "foregroundColor": _rgb("1E293B"),
                        },
                        "verticalAlignment":   "MIDDLE",
                        "wrapStrategy":        "WRAP",
                        "borders":             cell_border(),
                    }
                },
                "fields": ("userEnteredFormat(backgroundColor,textFormat,"
                           "verticalAlignment,wrapStrategy,borders)"),
            }
        })

        # ── Founder Name (col B = index 1) — bold ────────────────────────────
        batch_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId":          tab_sheet_id,
                    "startRowIndex":    row_idx,
                    "endRowIndex":      row_idx + 1,
                    "startColumnIndex": 1,
                    "endColumnIndex":   2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontFamily": "Arial",
                            "fontSize":   10,
                            "bold":       True,
                            "foregroundColor": _rgb("1B3A6B"),
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat",
            }
        })

        # ── Decision (col G = index 6) — colour by rating ────────────────────
        decision_val = str(row_data[6]).lower() if len(row_data) > 6 else ""
        dec_colors   = None
        for key, colors in DECISION_COLORS.items():
            if key in decision_val:
                dec_colors = colors
                break

        if dec_colors:
            batch_requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId":          tab_sheet_id,
                        "startRowIndex":    row_idx,
                        "endRowIndex":      row_idx + 1,
                        "startColumnIndex": 6,
                        "endColumnIndex":   7,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": _rgb(dec_colors["bg"]),
                            "textFormat": {
                                "fontFamily":      "Arial",
                                "fontSize":        10,
                                "bold":            True,
                                "foregroundColor": _rgb(dec_colors["fg"]),
                            },
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": ("userEnteredFormat(backgroundColor,textFormat,"
                               "horizontalAlignment)"),
                }
            })

        # ── Score % (col F = index 5) — bold, navy, centred ─────────────────
        batch_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId":          tab_sheet_id,
                    "startRowIndex":    row_idx,
                    "endRowIndex":      row_idx + 1,
                    "startColumnIndex": 5,
                    "endColumnIndex":   6,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontFamily":      "Arial",
                            "fontSize":        10,
                            "bold":            True,
                            "foregroundColor": _rgb("1B3A6B"),
                        },
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields": ("userEnteredFormat(textFormat,horizontalAlignment)"),
            }
        })

    # Send all formatting in one batch request
    if batch_requests:
        resp = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"requests": batch_requests},
        )
        if resp.status_code == 200:
            print(f"  Formatting applied to {num_rows} rows in 'Founder Pipeline'")
        else:
            print(f"  Formatting warning: {resp.status_code} — {resp.text[:200]}")


def append_results_to_sheet(results: list, date_str: str):
    """
    Writes scored companies to two tabs:
      - Pipeline         : every scored company, full scoring data
      - Founder Pipeline : top founders only (identified + score >= 65%), outreach tracker
    """
    sa_json  = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")

    print(f"DEBUG append: sa_json length={len(sa_json)}, sheet_id='{sheet_id}'")
    if not sa_json or not sheet_id:
        print("Google Sheets logging skipped — secrets not configured.")
        return

    if not results:
        print("No results to log.")
        return

    try:
        print("Logging to Google Sheets...")
        token = _get_access_token(sa_json)

        sheet_meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        meta           = requests.get(
            sheet_meta_url,
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        sheet_names = [s["properties"]["title"] for s in meta.get("sheets", [])]

        # ── Tab 1: Pipeline — every scored company ────────────────────────────
        _ensure_tab(sheet_meta_url, token, sheet_names, "Pipeline")
        _ensure_header(sheet_id, token, "Pipeline", COLUMNS)
        pipeline_rows = [company_to_row(r, date_str) for r in results]
        _append_rows(sheet_id, token, "Pipeline", pipeline_rows)

        # ── Tab 2: Founder Pipeline — top founders with identified names ──────
        _ensure_tab(sheet_meta_url, token, sheet_names, "Founder Pipeline")

        # Sheet already has title (row 1), subtitle (row 2), header (row 3)
        # Only write header if the tab is brand new (empty)
        fp_check = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Founder Pipeline!A3:A3",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        if not fp_check.get("values"):
            _ensure_header(sheet_id, token, "Founder Pipeline", FOUNDER_COLUMNS)

        top_founders = [
            r for r in sorted(results,
                               key=lambda x: x.get("score_pct", 0),
                               reverse=True)
            if r.get("founder", {}).get("founder_name", "unknown") not in ("", "unknown")
            and r.get("second_layer_alignment", False)
            and r.get("score_pct", 0) >= 65
        ]

        if top_founders:
            founder_rows  = [founder_to_row(r, date_str) for r in top_founders]
            start_row     = _get_last_row(sheet_id, token, "Founder Pipeline") + 1
            _append_rows(sheet_id, token, "Founder Pipeline", founder_rows)
            _format_founder_rows(
                sheet_id, sheet_meta_url, token,
                start_row, len(founder_rows), founder_rows
            )
            print(f"  {len(founder_rows)} founders added to 'Founder Pipeline'")
        else:
            print("  No identified founders to add to Founder Pipeline today")

    except Exception as e:
        print(f"Google Sheets logging failed: {e}")
        print("Pipeline will continue — email digest unaffected.")
