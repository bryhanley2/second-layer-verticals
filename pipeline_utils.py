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
import sys
import re
import json
from datetime import datetime, timezone
import anthropic
from anthropic import Anthropic
import gspread
from google.oauth2.service_account import Credentials

# ---------- Constants ----------
# NOTE: use `or` not the 2-arg get() default — GitHub Actions passes an unset
# `${{ vars.X }}` as an empty string, and get(key, default) returns "" for
# key-exists-but-empty. `or` falls back for both missing and empty.
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID") or "102k3pj7JjEhSXWgyBS144mgHd93MZywoWVyjWIonX50"
# Minimum weighted score to write a candidate to the sheet. Lowered from 65 to
# surface the 58-64 "early signal" band for review; raise via MIN_SCORE_PCT.
try:
    MIN_SCORE_PCT = int(os.environ.get("MIN_SCORE_PCT") or "58")
except ValueError:
    MIN_SCORE_PCT = 58

# Anthropic model for judgement-heavy calls — scoring, Second Layer eval, funding
# verification, vertical synthesis. Keep this capable. Override with PIPELINE_MODEL.
MODEL = os.environ.get("PIPELINE_MODEL") or "claude-opus-4-7"

# Cheaper model for the mechanical scrape-extraction step (pull company names out
# of a page — no judgement). ~5x cheaper; override with PIPELINE_MODEL_EXTRACT.
MODEL_EXTRACT = os.environ.get("PIPELINE_MODEL_EXTRACT") or "claude-haiku-4-5"

ALLOWED_STAGES = {
    "pre-seed", "preseed", "pre_seed", "seed",
    "angel", "angel round", "friends and family",
}
MAX_TOTAL_FUNDING = 10_000_000
MAX_COMPANY_AGE_YEARS = 5
MAX_MONTHS_SINCE_LAST_ROUND = 24
# A verified funding figure whose round date is older than this gets a STALE
# advisory — a newer round we didn't catch may have raised the real total.
STALE_FUNDING_MONTHS = 15

# Tightened thesis range for post-enrichment verification.
# The initial gate uses MAX_TOTAL_FUNDING ($10M) as a hard ceiling, but the thesis
# actually targets genuine seed ($1.8M-$4M). Companies between $4M and $10M pass the
# hard gate but are flagged as "above target range" so they can be reviewed, not
# silently treated as in-thesis.
TARGET_FUNDING_FLOOR = 1_800_000
TARGET_FUNDING_CEILING = 4_000_000

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


# ---------- LLM call health ----------
# Every Claude call in the pipeline is wrapped in try/except so one malformed
# response can't kill a whole run. The danger is the inverse failure: a systemic
# problem (bad key, wrong model id, sustained rate-limiting) gets swallowed and
# the run still "succeeds" while writing default/garbage scores. These helpers
# make that loud instead.
_LLM_ERRORS: list = []

# Errors that mean the whole run is misconfigured — no point scoring hundreds of
# companies against an endpoint that will reject every call.
_FATAL_LLM_ERRORS = (
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
    anthropic.NotFoundError,
)


def record_llm_error(context: str, exc: Exception) -> None:
    """Log an LLM call failure to stderr and remember it for the end-of-run summary.

    Raises RuntimeError on fatal misconfiguration (bad credentials / unknown
    model) so the run stops instead of producing a sheet full of defaults.
    """
    msg = f"[LLM ERROR] {context}: {type(exc).__name__}: {exc}"
    print(msg, file=sys.stderr)
    _LLM_ERRORS.append(msg)
    if isinstance(exc, _FATAL_LLM_ERRORS):
        raise RuntimeError(
            f"Fatal LLM configuration error ({type(exc).__name__}). "
            f"Check ANTHROPIC_API_KEY and PIPELINE_MODEL (currently '{MODEL}')."
        ) from exc


def llm_error_count() -> int:
    return len(_LLM_ERRORS)


def llm_error_summary() -> str:
    if not _LLM_ERRORS:
        return "No LLM call errors this run."
    lines = [f"{len(_LLM_ERRORS)} LLM call error(s) this run:"]
    lines.extend(f"  - {m}" for m in _LLM_ERRORS[:20])
    if len(_LLM_ERRORS) > 20:
        lines.append(f"  ... and {len(_LLM_ERRORS) - 20} more")
    return "\n".join(lines)


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
        if 0 < funding <= 3_000_000:
            return True, f"accepted (missing stage, funding ${funding:,.0f} implies pre-seed)"
        if funding == 0:
            # Zero could mean no data — pass with caution but funding gate will validate further
            return True, "accepted (missing stage and funding data — funding gate will validate)"
        return False, f"stage missing, funding ${funding:,.0f} too high to assume pre-seed/seed"
    # Explicitly reject Series A and later — pipeline is seed/pre-seed only now
    if any(s in stage for s in ("series a", "series_a", "series b", "series c", "series_b", "series_c")):
        return False, f"stage '{stage}' is Series A or later — excluded, seed/pre-seed only"
    for allowed in ALLOWED_STAGES:
        if allowed in stage:
            return True, f"stage '{stage}' allowed"
    return False, f"stage '{stage}' not seed-aligned"


def passes_funding_gate(candidate: dict):
    total = safe_float(candidate.get("total_funding_usd", 0))
    # If funding is 0 or missing, only pass if stage is explicitly pre-seed/seed
    # to avoid letting well-funded companies through on blank/missing funding fields.
    if total == 0:
        stage = str(candidate.get("last_funding_round", "") or candidate.get("stage", "")).strip().lower()
        if stage in {"pre-seed", "preseed", "seed", "angel", "grant", "accelerator", ""}:
            return True, "funding $0 (missing data) — stage suggests pre-seed, passing with caution"
        return False, f"funding $0 (missing data) and stage '{stage}' not pre-seed — likely data gap, rejecting"
    if total > MAX_TOTAL_FUNDING:
        return False, f"total funding ${total:,.0f} exceeds ${MAX_TOTAL_FUNDING:,.0f} cap"
    return True, f"funding ${total:,.0f} within cap"


def passes_age_gate(candidate: dict):
    founded_year = parse_year(candidate.get("founded_date") or candidate.get("founded_year") or "")
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


def verify_size_post_enrichment(candidate: dict):
    """
    Second-layer SIZE filter, run AFTER funding enrichment/verification.

    The initial passes_funding_gate() runs BEFORE enrichment, when many companies
    have total_funding_usd == 0 (missing data). Those pass on their stage LABEL alone.
    The problem: a company can be labeled "seed" but have actually raised $68M
    (e.g. Emerald AI) or $97M (e.g. Gridware) — the label lies, and the initial gate
    trusts it because the real number wasn't populated yet.

    This function re-checks size ONCE REAL FUNDING DATA EXISTS, and returns a status:
      - "REJECT"      : verified funding now exceeds the $10M hard cap -> remove from pipeline
      - "ABOVE_RANGE" : within the $10M cap but above the $4M thesis target -> keep, but flag
      - "IN_RANGE"    : within the $1.8M-$4M thesis sweet spot -> ideal
      - "BELOW_RANGE" : below $1.8M (very early / pre-seed-ish) -> keep, flag as earliest-stage
      - "UNVERIFIED"  : still no real funding figure -> cannot confirm, flag for manual check

    Returns (status: str, reason: str).
    """
    total = safe_float(candidate.get("total_funding_usd", 0))
    confidence = (candidate.get("_funding_confidence") or "").lower()
    unverified = candidate.get("_funding_unverified", False)

    # If funding is still 0 or the figure was never verified, we CANNOT confirm size.
    # Do not silently pass — flag it so it doesn't masquerade as in-thesis.
    if total == 0 or unverified or confidence in ("", "low", "unverified"):
        return "UNVERIFIED", (
            "size UNVERIFIED — no confirmed funding figure post-enrichment; "
            "manual funding check required before treating as in-thesis"
        )

    # Real, verified figure exists — now enforce the hard cap that the initial
    # gate could not enforce when data was missing.
    if total > MAX_TOTAL_FUNDING:
        return "REJECT", (
            f"REJECT — verified funding ${total:,.0f} exceeds ${MAX_TOTAL_FUNDING:,.0f} "
            f"hard cap (passed initial gate on missing/label data; real figure disqualifies)"
        )

    if total > TARGET_FUNDING_CEILING:
        return "ABOVE_RANGE", (
            f"ABOVE target range — ${total:,.0f} is within the ${MAX_TOTAL_FUNDING:,.0f} cap "
            f"but above the ${TARGET_FUNDING_CEILING:,.0f} thesis target; keep but flag as "
            f"more de-risked / pricier entry"
        )

    if total < TARGET_FUNDING_FLOOR:
        return "BELOW_RANGE", (
            f"BELOW target range — ${total:,.0f} is under ${TARGET_FUNDING_FLOOR:,.0f}; "
            f"earliest-stage entry, relationship-build play"
        )

    return "IN_RANGE", f"IN target range — ${total:,.0f} within ${TARGET_FUNDING_FLOOR:,.0f}-${TARGET_FUNDING_CEILING:,.0f} sweet spot"


# ---------- Funding-report confirmation ----------
_MONEY_RE = re.compile(r"\$\s?([\d,]+)")


def _figures_from_checks(checks) -> dict:
    """Pull {source_kind: usd} out of the _funding_checks audit strings.
    source_kind is one of crunchbase / sec / claude / other."""
    out = {}
    for line in checks or []:
        m = _MONEY_RE.search(str(line))
        if not m:
            continue
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if val <= 0:
            continue
        low = str(line).lower()
        kind = ("crunchbase" if low.startswith("crunchbase")
                else "sec" if "sec form d" in low
                else "claude" if low.startswith("claude")
                else "other")
        out[kind] = max(out.get(kind, 0.0), val)
    return out


def confirm_funding_report(candidate: dict):
    """Cross-check a *verified* funding figure for internal consistency, AFTER
    verify_zero_funding has run. Mutates the candidate: non-OK verdicts append to
    _funding_checks and downgrade _funding_confidence; an unresolvable CONFLICT
    clears the figure back to $0/unverified.

    Verdicts: OK | CONFLICT | STAGE_MISMATCH | STALE. Returns (verdict, note).
    Companies with no figure (total == 0) return ("OK", ...) — nothing to confirm.
    """
    candidate.setdefault("_funding_checks", [])
    total = safe_float(candidate.get("total_funding_usd", 0))
    if total <= 0:
        return "OK", "no figure to confirm"

    notes, verdict = [], "OK"

    # 1. Cross-source agreement --------------------------------------------------
    figs = _figures_from_checks(candidate.get("_funding_checks"))
    if len(figs) >= 2:
        lo, hi = min(figs.values()), max(figs.values())
        if hi - lo > 1_000_000 and hi > lo * 1.5:
            pairs = ", ".join(f"${v:,.0f} ({k})" for k, v in sorted(figs.items()))
            if "sec" in figs:
                # SEC Form D is a legal filing — trust it, keep the company, flag it.
                candidate["total_funding_usd"] = figs["sec"]
                total = figs["sec"]
                candidate["_funding_source"] = candidate.get("_funding_source") or "SEC Form D"
                notes.append(f"sources disagree ({pairs}) — using the SEC figure")
                verdict = "CONFLICT"
            else:
                notes.append(f"sources disagree ({pairs}) with no authoritative source — cleared to unverified")
                candidate["total_funding_usd"] = 0
                candidate["_funding_unverified"] = True
                candidate["_funding_confidence"] = "unverified"
                candidate["_funding_checks"].append("confirm: CONFLICT — " + notes[-1])
                return "CONFLICT", notes[-1]

    # 2. Stage / amount plausibility -------------------------------------------
    stage = str(candidate.get("last_funding_round", "") or candidate.get("stage", "")).strip().lower()
    if stage in {"pre-seed", "preseed", "pre_seed"} and total > 5_000_000:
        verdict = "STAGE_MISMATCH"
        notes.append(f"labelled '{stage}' but ${total:,.0f} verified — likely mislabelled or later-stage")
    elif stage == "seed" and total > 12_000_000:
        verdict = "STAGE_MISMATCH"
        notes.append(f"labelled 'seed' but ${total:,.0f} verified")

    # 3. Staleness ------------------------------------------------------------
    d = parse_date(candidate.get("last_funding_date", ""))
    if d:
        months = (datetime.now() - d).days / 30
        if months > STALE_FUNDING_MONTHS:
            notes.append(f"figure is ~{months:.0f} months old — current total may be higher")
            if verdict == "OK":
                verdict = "STALE"

    if verdict != "OK":
        cur = (candidate.get("_funding_confidence") or "").lower()
        if verdict in ("CONFLICT", "STAGE_MISMATCH"):
            # one notch down; STAGE_MISMATCH on a real figure should not read as a clean seed number
            candidate["_funding_confidence"] = {"high": "medium", "medium": "low"}.get(cur, cur or "low")
        for n in notes:
            candidate["_funding_checks"].append(f"confirm: {verdict} — {n}")

    return verdict, "; ".join(notes) or "consistent"


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
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Claude sometimes prefixes "SCORE: 3 | ..." or "Score|..." — pull the
        # first 1-3 digit in the text rather than assuming position 0.
        m = re.search(r"[123]", text)
        if not m:
            raise ValueError(f"no 1-3 score in Second Layer response: {text[:80]!r}")
        score = int(m.group(0))
        reason = text.split("|", 1)[1].strip() if "|" in text else text[m.end():].lstrip(" :|-").strip()
        return score, reason[:200]
    except Exception as e:
        record_llm_error(f"Second Layer eval for {candidate.get('name')}", e)
        # Fail CLOSED: callers treat score >= 2 as "passes the thesis filter", so a
        # failed eval must score 0/1, never the old default of 2 that let it through.
        return 0, "Second Layer eval failed (LLM error) — excluded"


# ---------- 9-factor scoring ----------
def score_candidate(ai_client: Anthropic, candidate: dict, sl_reason: str):
    _raised = safe_float(candidate.get("total_funding_usd", 0))
    if _raised > 0:
        raised_line = f"${_raised:,.0f}"
    else:
        # Don't show "$0" — it reads to the model as "raised nothing / not real".
        raised_line = (f"not publicly disclosed (early-stage; sourced via "
                       f"{candidate.get('_source', 'the pipeline')})")
    founded = candidate.get("founded_date") or candidate.get("founded_year") or "unknown"
    site_text = str(candidate.get("_site_text", "")).strip()
    site_block = f"\n\nFrom the company's own website:\n{site_text}\n" if site_text else ""
    prompt = f"""Score this seed-stage company on 9 factors (1-10 each).

Company: {candidate.get("name")}
Description: {str(candidate.get("description", ""))}
Stage: {candidate.get("last_funding_round", candidate.get("stage", "unknown"))}
Total raised: {raised_line}
Headcount: {candidate.get("headcount", "unknown")}
Founded: {founded}
HQ: {candidate.get("hq_city", "")}, {candidate.get("hq_country", "")}
Second Layer assessment: {sl_reason}{site_block}

Score each factor 1-10 using the anchors. If the evidence for a factor is
genuinely missing, score it 4 (not 5) and say so in RISKS — thin data is a real
negative at seed, not a neutral. Do not invent specifics. Use the website text
above for traction, product depth, and team signals.

1A. Founder-Market Fit — 9: founder built/operated the exact system this
   replaces, or is a recognized authority in the domain. 6: adjacent-domain
   operator or strong technical background in the space. 3: no stated relevant
   background. 1: background contradicts the problem.
1B. Tech Differentiation — 9: defensible technical moat (proprietary data,
   hard integration, novel method) clearly described. 6: solid product, some
   differentiation but replicable. 3: thin wrapper / obvious approach.
1C. Founder Commitment — 9: full-time, second-time founder or left a senior
   role for this. 6: full-time, first-time. 3: unclear / side project signals.
2A. Product-Market Fit — 9: named paying customers or a waitlist/pipeline
   described on the site. 6: live product, design partners, early usage. 3:
   pre-product or vague "working with teams". 1: idea stage.
3A. Market Size — 9: clear >$1B TAM driven by a regulatory/structural mandate.
   6: solid >$1B but discretionary or fragmented. 3: niche / <$500M.
3B. Timing — 9: a specific mandate, deadline, or structural shift makes this
   urgent NOW (name it). 6: strong tailwind, no hard catalyst. 3: "someday".
5. Traction Quality — 9: named enterprise pilots/contracts or revenue on the
   site. 6: LOIs, design partners, or a notable logo. 3: none stated. 1: none
   and pre-product.
6. Capital Efficiency — 9: meaningful traction on <$3M or a lean team for the
   stage. 6: normal seed burn. 3: large raise / headcount with little to show.
   Score 5 if funding is undisclosed and headcount is unknown.
7. Investor Signal — 9: a top specialist fund led (name it). 6: a known seed
   fund or strong accelerator. 3: unknown or unstated. Score 4 if no investor
   information is available.

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
RISKS:primary risk (<=25 words)
FOUNDERS:Founder name(s), title(s), and prior background in <=40 words. CRITICAL: If you do not know the specific founder names from a verifiable source, write "UNVERIFIED — needs manual lookup" instead of guessing. NEVER fabricate names like "Eric Ness" when the actual co-founder is "Eric Ryan". NEVER complete the pattern of a plausible-sounding bio. If uncertain about ANY founder, mark the whole field UNVERIFIED."""

    try:
        response = ai_client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        scores = {}
        meta = {"summary": "", "strengths": "", "risks": "", "founders": ""}

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
                    scores[key] = max(1, min(10, int(digits))) if digits else 4
                except ValueError:
                    scores[key] = 4
            elif key.upper() == "SUMMARY":
                meta["summary"] = val
            elif key.upper() == "STRENGTHS":
                meta["strengths"] = val
            elif key.upper() == "RISKS":
                meta["risks"] = val
            elif key.upper() == "FOUNDERS":
                meta["founders"] = val

        parsed = len(scores)
        weighted = 0.0
        for factor, weight in FACTOR_WEIGHTS.items():
            weighted += scores.get(factor, 4) * weight
        pct = round(weighted * 10, 1)
        if parsed < 7:  # the model didn't return most factors — don't trust the number
            record_llm_error(
                f"9-factor scoring for {candidate.get('name')}",
                ValueError(f"only {parsed}/9 factors parsed"),
            )
            pct = 0.0

        return {
            "scores": scores,
            "weighted_pct": pct,
            "summary": meta["summary"],
            "strengths": meta["strengths"],
            "risks": meta["risks"],
            "founders": meta["founders"],
        }
    except Exception as e:
        record_llm_error(f"9-factor scoring for {candidate.get('name')}", e)
        # weighted_pct 0 drops the candidate at the threshold check — fail closed.
        return {"scores": {}, "weighted_pct": 0, "summary": "", "strengths": "",
                "risks": f"scoring failed (LLM error): {e}", "founders": ""}


def decision_from_score(pct: float) -> str:
    if pct >= 82:
        return "★★★★★ STRONG YES"
    if pct >= 72:
        return "★★★★ YES"
    if pct >= 64:
        return "★★★ DEEP DIVE"
    if pct >= 55:
        return "★★ WATCH — early signal"
    return "★ PASS"


# ---------- Sheet writers ----------
PIPELINE_HEADERS = [
    "Date", "Company", "Stage", "Total Raised", "Vertical", "Source",
    "Second Layer Logic", "Description", "Passed Gates",
    "Founders",
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
    tab = ensure_tab(client, tab_name, headers=PIPELINE_HEADERS, cols=len(PIPELINE_HEADERS) + 2)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for c in scored:
        cand = c["candidate"]
        s = c.get("scores", {})
        # Make funding-verification status visible in the sheet. If the funding figure
        # was never verified against a citable source, mark it clearly rather than
        # writing a bare number that looks authoritative.
        funding_val = safe_float(cand.get("total_funding_usd", 0))
        conf = (cand.get("_funding_confidence") or "").lower()
        size_status = cand.get("_size_status", "")
        src = str(cand.get("_funding_source") or "").strip()
        if conf in ("low", "unverified") or cand.get("_funding_unverified"):
            # src here is the "tried — crunchbase: ...; sec form d: ...; claude: ..." trail.
            funding_display = f"UNVERIFIED · {src}" if src.startswith("tried") else "UNVERIFIED"
        else:
            label = {"high": "", "medium": " (single source)"}.get(conf, "")
            short_src = src.split("://", 1)[-1].split("/", 1)[0] if src.startswith("http") else src
            funding_display = f"{funding_val:,.0f}{label}" + (f" · {short_src}" if short_src else "")
        # Append the thesis-range size status (IN_RANGE / ABOVE_RANGE / BELOW_RANGE)
        # so a reviewer sees at a glance whether a company is in the $1.8M-$4M sweet
        # spot or merely under the $10M hard cap.
        if size_status and size_status not in ("IN_RANGE",):
            funding_display = f"{funding_display} [{size_status}]"
        rows.append([
            now,
            cand.get("name", ""),
            cand.get("last_funding_round", cand.get("stage", "")),
            funding_display,
            vertical_label or cand.get("industry", ""),
            cand.get("_source", "unknown"),
            c.get("sl_reason", ""),
            str(cand.get("description", ""))[:400],
            "Yes",
            c.get("founders", ""),
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
