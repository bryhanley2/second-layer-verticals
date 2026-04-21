"""
Pipeline Utilities
==================
Shared helpers used by sourcer.py and vertical_pipeline.py.
Contains the three hard gates, 9-factor scoring rubric, and Google Sheets I/O.

Import this from other pipeline files:
    from pipeline_utils import (
        passes_all_gates, score_candidate, write_to_pipeline_tab,
        evaluate_second_layer_fit, decision_from_score,
    )
"""

import os
import json
from datetime import datetime, timezone
from anthropic import Anthropic
import gspread
from google.oauth2.service_account import Credentials

# ---------- Constants ----------
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "102k3pj7JjEhSXWgyBS144mgHd93MZywoWVyjWIonX50")
MIN_SCORE_PCT = 65

ALLOWED_STAGES = {
    "pre-seed", "preseed", "pre_seed", "seed", "series a", "series_a",
    "angel", "angel round", "friends and family",
}
MAX_TOTAL_FUNDING = 15_000_000
MAX_COMPANY_AGE_YEARS = 5
MAX_MONTHS_SINCE_LAST_ROUND = 24

# 9-factor rubric weights
FACTOR_WEIGHTS = {
    "1A": 0.14, "1B": 0.11, "1C": 0.10,
    "2A": 0.15,
    "3A": 0.12, "3B": 0.11,
    "5": 0.10, "6": 0.10, "7": 0.07,
}


# ---------- Google Sheets client ----------
def get_sheet_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON not set")
    creds_dict = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_anthropic_client():
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ---------- Type coercion helpers ----------
def safe_float(v) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def parse_year(v):
    if not v:
        return None
    try:
        s = str(v).strip()
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
    except (ValueError, AttributeError):
        pass
    return None


def parse_date(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y"):
        try:
            return datetime.strptime(s[:10] if len(s) >= 10 else s, fmt)
        except ValueError:
            continue
    return None


# ---------- Three hard gates ----------
def passes_stage_gate(candidate: dict):
    stage = str(candidate.get("last_funding_round", "") or candidate.get("stage", "")).strip().lower()
    if not stage or stage in {"unknown", "none"}:
        funding = safe_float(candidate.get("total_funding_usd", 0))
        if funding <= 3_000_000:
            return True, "accepted (missing stage, low funding implies pre-seed)"
        return False, f"stage missing, funding ${funding:,.0f} too high to assume pre-seed"
    for allowed in ALLOWED_STAGES:
        if allowed in stage:
            return True, f"stage '{stage}' allowed"
    return False, f"stage '{stage}' not seed-aligned"


def passes_funding_gate(candidate: dict):
    total = safe_float(candidate.get("total_funding_usd", 0))
    if total > MAX_TOTAL_FUNDING:
        return False, f"total funding ${total:,.0f} exceeds ${MAX_TOTAL_FUNDING:,.0f} cap"
    return True, f"funding ${total:,.0f} within cap"


def passes_age_gate(candidate: dict):
    founded_year = parse_year(candidate.get("founded_date", ""))
    if founded_year:
        age = datetime.now().year - founded_year
        if age > MAX_COMPANY_AGE_YEARS:
            return False, f"founded {founded_year}, {age} years old"
    last_round_date = parse_date(candidate.get("last_funding_date", ""))
    if last_round_date:
        months_since = (datetime.now() - last_round_date).days / 30
        if months_since > MAX_MONTHS_SINCE_LAST_ROUND:
            return False, f"last round {months_since:.0f} months ago, stale"
    return True, "age and recency OK"


def passes_all_gates(candidate: dict):
    """Returns (passed: bool, reason: str)."""
    for gate in (passes_stage_gate, passes_funding_gate, passes_age_gate):
        ok, reason = gate(candidate)
        if not ok:
            return False, reason
    return True, "all gates passed"


# ---------- Second Layer thesis filter ----------
def evaluate_second_layer_fit(ai_client: Anthropic, candidate: dict):
    """
    Returns (score 1-3, reason).
    1 = fails (company IS the trend)
    2 = borderline
    3 = strong fit
    """
    prompt = f"""Evaluate Second Layer investment thesis fit.

Second Layer = company solves problems CREATED BY a dominant trend, NOT a company that IS the trend.

Examples:
- DOMINANT: satellite proliferation → SECOND LAYER: RF detection for maritime blind spots (Unseenlabs)
- DOMINANT: healthcare AI adoption → SECOND LAYER: AI model monitoring (post-deployment compliance)
- FAILS: another satellite manufacturer; another foundation model

Company: {candidate.get("name")}
Description: {str(candidate.get("description", ""))[:800]}
Industry: {candidate.get("industry", "")}

Rate 1-3:
1 = Fails (IS the trend itself)
2 = Borderline/unclear
3 = Strong Second Layer fit

Respond with ONLY: SCORE|reason (max 30 words)"""

    try:
        response = ai_client.messages.create(
            model="claude-opus-4-7",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parts = text.split("|", 1)
        score = int(parts[0].strip()[0])
        reason = parts[1].strip() if len(parts) > 1 else ""
        return score, reason
    except Exception as e:
        print(f"    Second Layer eval error for {candidate.get('name')}: {e}")
        return 2, "eval error, defaulted to borderline"


# ---------- 9-factor scoring ----------
def score_candidate(ai_client: Anthropic, candidate: dict, sl_reason: str):
    prompt = f"""Score this seed-stage company on 9 factors (1-10 each).

Company: {candidate.get("name")}
Description: {str(candidate.get("description", ""))}
Stage: {candidate.get("last_funding_round", candidate.get("stage", "unknown"))}
Total raised: ${safe_float(candidate.get('total_funding_usd', 0)):,.0f}
Headcount: {candidate.get("headcount", "unknown")}
Founded: {candidate.get("founded_date", "unknown")}
HQ: {candidate.get("hq_city", "")}, {candidate.get("hq_country", "")}
Second Layer assessment: {sl_reason}

Score 1-10 (10=exceptional, 5=average, 1=weak):
1A. Founder-Market Fit
1B. Tech Differentiation
1C. Founder Commitment
2A. Product-Market Fit
3A. Market Size (TAM >$1B for max)
3B. Timing (tailwinds)
5. Traction Quality (named pilots/contracts)
6. Capital Efficiency (right burn for stage)
7. Investor Signal

Format EXACTLY:
1A:N
1B:N
1C:N
2A:N
3A:N
3B:N
5:N
6:N
7:N
SUMMARY:one-sentence overall
STRENGTHS:primary strength (<=25 words)
RISKS:primary risk (<=25 words)"""

    try:
        response = ai_client.messages.create(
            model="claude-opus-4-7",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        scores = {}
        meta = {"summary": "", "strengths": "", "risks": ""}

        for line in text.split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key in {"1A", "1B", "1C", "2A", "3A", "3B", "5", "6", "7"}:
                try:
                    digits = ''.join(c for c in val if c.isdigit())[:2]
                    scores[key] = int(digits) if digits else 5
                except ValueError:
                    scores[key] = 5
            elif key.upper() == "SUMMARY":
                meta["summary"] = val
            elif key.upper() == "STRENGTHS":
                meta["strengths"] = val
            elif key.upper() == "RISKS":
                meta["risks"] = val

        weighted = 0.0
        for factor, weight in FACTOR_WEIGHTS.items():
            weighted += scores.get(factor, 5) * weight
        pct = round(weighted * 10, 1)

        return {
            "scores": scores,
            "weighted_pct": pct,
            "summary": meta["summary"],
            "strengths": meta["strengths"],
            "risks": meta["risks"],
        }
    except Exception as e:
        print(f"    Scoring error for {candidate.get('name')}: {e}")
        return {"scores": {}, "weighted_pct": 0, "summary": "", "strengths": "", "risks": f"Error: {e}"}


def decision_from_score(pct: float) -> str:
    if pct >= 85:
        return "★★★★★ STRONG YES"
    if pct >= 75:
        return "★★★★ YES"
    if pct >= 65:
        return "★★★ DEEP DIVE"
    if pct >= 55:
        return "★★ PROBABLY PASS"
    return "★ HARD PASS"


# ---------- Sheet writers ----------
PIPELINE_HEADERS = [
    "Date", "Company", "Stage", "Total Raised", "Vertical", "Source",
    "Second Layer Logic", "Description", "Passed Gates",
    "1A_FMF", "1B_Tech", "1C_Commit", "2A_PMF", "3A_TAM", "3B_Timing",
    "5_TrxQl", "6_CapEff", "7_Investor",
    "Weighted %", "Decision", "Summary", "Strengths", "Risks",
    "Website", "LinkedIn",
]


def ensure_tab(client, tab_name: str, headers: list = None, rows: int = 1000, cols: int = 25):
    """Get or create a worksheet tab, optionally seeding headers on creation."""
    sheet = client.open_by_key(SHEET_ID)
    try:
        return sheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        tab = sheet.add_worksheet(title=tab_name, rows=rows, cols=cols)
        if headers:
            tab.append_row(headers)
        return tab


def read_existing_names(client, tab_name: str) -> set:
    """Get set of company names already in a given tab for dedup."""
    try:
        sheet = client.open_by_key(SHEET_ID)
        tab = sheet.worksheet(tab_name)
        rows = tab.get_all_records()
        return {str(r.get("Company", "")).strip().lower() for r in rows if r.get("Company")}
    except gspread.WorksheetNotFound:
        return set()


def write_scored_candidates(client, tab_name: str, scored: list, vertical_label: str = ""):
    """Append scored candidates to the specified tab."""
    tab = ensure_tab(client, tab_name, headers=PIPELINE_HEADERS)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for c in scored:
        cand = c["candidate"]
        s = c.get("scores", {})
        rows.append([
            now,
            cand.get("name", ""),
            cand.get("last_funding_round", cand.get("stage", "")),
            safe_float(cand.get("total_funding_usd", 0)),
            vertical_label or cand.get("industry", ""),
            cand.get("_source", "Crustdata"),
            c.get("sl_reason", ""),
            str(cand.get("description", ""))[:400],
            "Yes",
            s.get("1A", ""), s.get("1B", ""), s.get("1C", ""),
            s.get("2A", ""), s.get("3A", ""), s.get("3B", ""),
            s.get("5", ""), s.get("6", ""), s.get("7", ""),
            c.get("weighted_pct", 0),
            c.get("decision", ""),
            c.get("summary", ""),
            c.get("strengths", ""),
            c.get("risks", ""),
            cand.get("website", ""),
            cand.get("linkedin_url", ""),
        ])
    if rows:
        tab.append_rows(rows)
        print(f"Wrote {len(rows)} candidates to '{tab_name}' tab")


# ---------- Email (silent fail) ----------
def send_email_digest(subject: str, body: str):
    """Send email via Gmail SMTP. Fails silently if creds are missing or SMTP errors."""
    try:
        import smtplib
        from email.mime.text import MIMEText

        user = os.environ.get("GMAIL_USER")
        password = os.environ.get("GMAIL_APP_PASSWORD")
        to_addr = os.environ.get("EMAIL_RECIPIENT", user)

        if not user or not password:
            print("Email skipped: credentials not set")
            return

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.send_message(msg)
        print("Email sent successfully")
    except Exception as e:
        print(f"Email skipped: {e}")
