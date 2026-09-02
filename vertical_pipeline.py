"""
Second Layer Vertical Pipeline
================================================
Runs on-demand for a specific vertical (0-20). Combines free sources:
  1. YC Companies    — yc-oss dataset filtered by vertical keywords + recent batch
  2. SEC Form D      — EDGAR filings keyword-matched per vertical
  3. TechCrunch      — venture/startup feeds keyword-filtered
  4. Vertical RSS    — sector publications parsed for seed funding announcements
  5. Claude Research — vertical-targeted research prompts
  6. Extra sources   — YC Launch HN posts, Product Hunt, VC newsletters
                       (new_sources.py; set EXTRA_SOURCES=0 to skip)
  7. Scrape layer    — verticals with scrape_targets: HTML fetch (static +
                       headless) + Claude extraction + run-over-run diff
                       (set SCRAPE_LAYER=0 to skip)

After scoring, the top DIGEST_TOP_N candidates get a website-only contact
lookup (public email + LinkedIn; ENRICH_CONTACTS=0 to skip) and an outreach
digest is emailed to EMAIL_RECIPIENT.

All candidates pass through the three hard gates before scoring, then the
Second Layer thesis filter, then 9-factor scoring. Writes to the
"Vertical Pipeline" tab with the vertical name annotated.

Usage:
  VERTICAL_INDEX=0 python vertical_pipeline.py       # Energy
  VERTICAL_INDEX=10 python vertical_pipeline.py      # Healthcare
  VERTICAL_INDEX=20 python vertical_pipeline.py      # Consumer Health Brands
  (no override) → rotates by day of year

  INDUSTRY_QUERY="precision fermentation" python vertical_pipeline.py
      → on-demand: Claude synthesizes a vertical (keywords / feeds / search
        terms) from the free-text query, then runs the full pipeline for it and
        writes to the "On-Demand Pipeline" tab. Overrides VERTICAL_INDEX.

Required env vars:
  ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID
"""

import os
import sys
import json
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta
import requests
import feedparser
from pipeline_utils import (
    get_sheet_client, get_anthropic_client, SHEET_ID, MODEL, MODEL_EXTRACT,
    passes_all_gates, evaluate_second_layer_fit, score_candidate,
    verify_size_post_enrichment, confirm_funding_report,
    decision_from_score, write_scored_candidates, read_existing_names,
    send_email_digest, MIN_SCORE_PCT, safe_float, ensure_tab,
    record_llm_error, llm_error_count, llm_error_summary,
)
from vertical_sources import (
    get_vertical, get_vertical_by_day_of_year, synthesize_vertical,
    get_scrape_targets, passes_scrape_filter,
)
from new_sources import source_yc_launches, source_producthunt, VC_NEWSLETTER_FEEDS
from contact_enrich import enrich_contact, scan_site_for_funding, fetch_company_context

VERTICAL_TAB = "Vertical Pipeline"
# On-demand runs (INDUSTRY_QUERY set) write here instead, to keep the curated
# vertical data separate from ad-hoc industry requests.
ON_DEMAND_TAB = "On-Demand Pipeline"

# Extra early-signal sources (YC Launches, Product Hunt, VC newsletters) run in
# STEP 1 unless EXTRA_SOURCES=0.
EXTRA_SOURCES_ENABLED = os.environ.get("EXTRA_SOURCES", "1").strip() != "0"

# Proprietary scrape layer (HTML targets + run-over-run diff). Runs for any
# vertical that defines scrape_targets; a no-op for the rest. Set SCRAPE_LAYER=0
# (legacy alias: V21_SCRAPE=0) to skip it entirely.
SCRAPE_LAYER_ENABLED = (os.environ.get("SCRAPE_LAYER") or os.environ.get("V21_SCRAPE") or "1").strip() != "0"
SCRAPE_STATE_TAB = "Scrape Seen"
# Cap on how many never-before-seen companies one scrape run pushes into the
# pipeline — protects the first run (empty state) from processing whole portfolios.
try:
    SCRAPE_MAX_NEW = int(os.environ.get("SCRAPE_MAX_NEW") or os.environ.get("V21_SCRAPE_MAX_NEW") or "50")
except ValueError:
    SCRAPE_MAX_NEW = 50
# A scrape company that never resolves (keeps scoring in the 40-57% band) is
# retried each run until it's this many days old, then given up on.
try:
    SCRAPE_RETRY_DAYS = int(os.environ.get("SCRAPE_RETRY_DAYS") or "60")
except ValueError:
    SCRAPE_RETRY_DAYS = 60

# Claude research fan-out cap (each search term = one Claude call).
try:
    RESEARCH_MAX_QUERIES = int(os.environ.get("RESEARCH_MAX_QUERIES") or "12")
except ValueError:
    RESEARCH_MAX_QUERIES = 12

# Outreach digest: scrape each top candidate's website for a public email
# (ENRICH_CONTACTS=0 to skip) and send that many in the email digest.
ENRICH_CONTACTS = os.environ.get("ENRICH_CONTACTS", "1").strip() != "0"
try:
    DIGEST_TOP_N = int(os.environ.get("DIGEST_TOP_N") or "10")
except ValueError:
    DIGEST_TOP_N = 10

# Recent YC batches considered "early enough" for the stage gate.
# Adjust as new batches are announced.
RECENT_YC_BATCHES = {"W23", "S23", "W24", "S24", "F24", "W25", "S25", "F25", "X25", "W26", "S26"}


# ============================================================================
# Source 1: YC Companies
# ============================================================================
def source_vertical_yc(keywords: list, vertical_name: str) -> list:
    """
    Pull the full YC company dataset (yc-oss) and filter by vertical keywords.
    Free, structured, and refreshed by yc-oss on every YC batch.
    """
    candidates = []
    url = "https://yc-oss.github.io/api/companies/all.json"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        companies = resp.json()
    except Exception as e:
        print(f"[YC] Error fetching company list: {e}")
        return []

    kw_lower = [k.lower() for k in keywords]
    for co in companies:
        # Build a searchable text blob from the company's fields
        blob = " ".join(str(co.get(f, "")) for f in (
            "name", "one_liner", "long_description", "industry", "subindustry", "tags"
        )).lower()

        # Keyword match against the vertical
        if not any(k in blob for k in kw_lower):
            continue

        batch = str(co.get("batch", "")).upper().replace(" ", "")
        # Only keep recent batches to respect the stage/age gates
        if batch and batch not in RECENT_YC_BATCHES:
            continue

        candidates.append({
            "name": str(co.get("name", ""))[:80],
            "website": co.get("website", "") or co.get("url", ""),
            "description": (co.get("one_liner") or co.get("long_description") or "")[:500],
            "industry": vertical_name,
            "hq_city": co.get("all_locations", "") or "",
            "hq_country": "United States",
            "founded_date": "",
            "headcount": co.get("team_size", 0) or 0,
            "total_funding_usd": 0,           # YC dataset has no funding figure
            "last_funding_round": "seed",     # default; gate + verification refine this
            "last_funding_date": "",
            "linkedin_url": "",
            "yc_batch": batch,
            "_source": f"YC {batch}" if batch else "YC",
        })

    print(f"[YC] {len(candidates)} candidates matched vertical keywords")
    return candidates


# ============================================================================
# Source 1b: SEC EDGAR Form D filings (cross-vertical, keyword-filtered)
# ============================================================================
def source_sec_form_d(keywords: list, vertical_name: str, days_back: int = 30) -> list:
    """
    Search SEC EDGAR full-text search for recent Form D filings (private
    placements / seed & venture rounds) matching the vertical keywords.

    Form D is filed within 15 days of a private raise, so this catches rounds
    that never get press coverage. Data is sparse (name + date), so these
    candidates rely on the Step 1b funding-verification pass.

    SEC requires a descriptive User-Agent header with contact info.
    """
    from datetime import timedelta
    candidates = []
    headers = {"User-Agent": "SecondLayerVC Research bryanhanleyvc@gmail.com"}
    end = datetime.now()
    start = end - timedelta(days=days_back)
    seen_names = set()

    # Query EDGAR full-text search once per keyword (cap to top 4 to stay polite)
    for kw in keywords[:4]:
        url = (
            "https://efts.sec.gov/LATEST/search-index"
            f"?q=%22{kw.replace(' ', '%20')}%22&forms=D"
            f"&dateRange=custom&startdt={start.strftime('%Y-%m-%d')}&enddt={end.strftime('%Y-%m-%d')}"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                continue
            hits = resp.json().get("hits", {}).get("hits", [])
            for h in hits[:15]:
                src = h.get("_source", {})
                names = src.get("display_names", []) or []
                if not names:
                    continue
                # display_names look like "Acme Inc (CIK 0001234567)"
                raw = names[0]
                name = re.sub(r"\s*\(CIK.*\)\s*", "", raw).strip()[:80]
                key = name.lower()
                if not name or key in seen_names:
                    continue
                # Form D is filed by funds, SPVs, DSTs and holding entities too —
                # keyword search drags them in. Drop anything that isn't an
                # operating company by name.
                if _FUND_ENTITY_RE.search(name):
                    continue
                seen_names.add(key)
                candidates.append({
                    "name": name,
                    "website": "",
                    "description": f"Form D filing matched '{kw}' in {vertical_name}",
                    "industry": vertical_name,
                    "hq_city": "", "hq_country": "United States",
                    "founded_date": "", "headcount": 0,
                    "total_funding_usd": 0,        # verified in Step 1b
                    "last_funding_round": "seed",
                    "last_funding_date": src.get("file_date", ""),
                    "linkedin_url": "",
                    "_source": "SEC Form D",
                })
        except Exception as e:
            print(f"[SEC Form D '{kw}'] Error: {e}")

    print(f"[SEC Form D] {len(candidates)} candidates from filings")
    return candidates


# ============================================================================
# Source 1c: TechCrunch funding coverage (cross-vertical, keyword-filtered)
# ============================================================================
_FUNDING_HEADLINE_RE = re.compile(
    r"([A-Z][A-Za-z0-9.\-& ]{2,40})\s+(?:raises?|secures?|closes?|lands?|nabs?|bags?|gets|nets|banks|snags)\s+\$(\d+(?:\.\d+)?)\s*([MK])",
    re.IGNORECASE,
)
_HEADLINE_VERB_RE = re.compile(
    r"\b(wants|plans|aims|hopes|is |are |launches|unveils|debuts|introduces|to make|to help|"
    r"that |which |how |why |after |amid |could |says |thinks|bets|pivots)\b",
    re.I,
)
_NAME_ONLY_RAISE_RE = re.compile(
    r"^([A-Z][A-Za-z0-9.\-& ]{1,40}?)\s+(?:raises?|secures?|closes?|lands?|nabs?|bags?|gets|nets|banks|snags)\b",
)


_GENERIC_NAME = {
    "our portfolio", "portfolio", "learn more", "read more", "case study",
    "view all", "see all", "load more", "companies", "our companies", "team",
    "our team", "about", "about us", "contact", "contact us", "investments",
    "our investments", "back", "home", "explore", "news", "insights", "the team",
}


def _plausible_company_name(name: str) -> bool:
    name = (name or "").strip()
    if not name or name.lower() in _GENERIC_NAME or _HEADLINE_VERB_RE.search(name):
        return False
    return 1 <= len(name.split()) <= 5


def _company_from_funding_headline(title: str):
    """(name, funding_usd) from a funding headline, or (None, 0) if the title
    isn't 'Company raises $N' shaped — better to drop than emit a headline."""
    m = _FUNDING_HEADLINE_RE.search(title)
    if m:
        name = m.group(1).strip()
        usd = float(m.group(2)) * (1_000_000 if m.group(3).upper() == "M" else 1_000)
        return (name[:80] if _plausible_company_name(name) else None), usd
    m2 = _NAME_ONLY_RAISE_RE.match(title)
    if m2:
        name = m2.group(1).strip()
        return (name[:80] if _plausible_company_name(name) else None), 0.0
    return None, 0.0


def source_techcrunch(keywords: list, vertical_name: str) -> list:
    """Parse TechCrunch venture/startup feeds for seed rounds matching the vertical."""
    candidates = []
    tc_feeds = [
        "https://techcrunch.com/category/venture/feed/",
        "https://techcrunch.com/category/startups/feed/",
        "https://techcrunch.com/tag/seed-funding/feed/",
    ]
    kw_lower = [k.lower() for k in keywords]
    seed_keywords = ["seed", "pre-seed", "series a"]

    for feed_url in tc_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:40]:
                title = (entry.get("title", "") or "").strip()
                summary = (entry.get("summary", "") or "").strip()
                blob = f"{title} {summary}".lower()
                # Must match the vertical AND look seed-stage
                if not any(k in blob for k in kw_lower):
                    continue
                if not any(s in blob for s in seed_keywords):
                    continue
                name, funding_usd = _company_from_funding_headline(title)
                if not name:
                    continue
                if funding_usd > 15_000_000:
                    continue
                candidates.append({
                    "name": name,
                    "website": entry.get("link", ""),
                    "description": summary[:500],
                    "industry": vertical_name,
                    "hq_city": "", "hq_country": "United States",
                    "founded_date": "", "headcount": 0,
                    "total_funding_usd": funding_usd,
                    "last_funding_round": "seed",
                    "last_funding_date": entry.get("published", ""),
                    "linkedin_url": "",
                    "_source": "TechCrunch",
                })
        except Exception as e:
            print(f"[TechCrunch {feed_url}] Error: {e}")

    print(f"[TechCrunch] {len(candidates)} candidates matched vertical")
    return candidates


# ============================================================================
# Source 2: Vertical-specific RSS feeds
# ============================================================================
def source_vertical_rss(rss_urls: list, vertical_name: str) -> list:
    """Parse vertical-specific publications for seed-stage funding announcements."""
    candidates = []
    seed_keywords = ["seed", "pre-seed", "series a", "$1m", "$2m", "$3m", "$5m", "$10m", "$15m"]

    for feed_url in rss_urls:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title = (entry.get("title", "") or "").strip()
                summary = (entry.get("summary", "") or "").strip()
                combined = f"{title} {summary}".lower()
                if not any(k in combined for k in seed_keywords):
                    continue
                # Only keep items where a real "Company raises $N" name can be
                # pulled from the title — otherwise it's a trend/analysis headline.
                name, funding_usd = _company_from_funding_headline(title)
                if not name:
                    continue
                if funding_usd > 15_000_000:
                    continue

                candidates.append({
                    "name": name[:80],
                    "website": entry.get("link", ""),
                    "description": summary[:500],
                    "industry": vertical_name,
                    "hq_city": "", "hq_country": "United States",
                    "founded_date": "", "headcount": 0,
                    "total_funding_usd": funding_usd, "last_funding_round": "seed",
                    "last_funding_date": entry.get("published", ""),
                    "linkedin_url": "",
                    "_source": f"RSS ({feed_url.split('/')[2]})",
                })
        except Exception as e:
            print(f"[RSS {feed_url}] Error: {e}")

    print(f"[Vertical RSS] {len(candidates)} candidates from {len(rss_urls)} feeds")
    return candidates


# ============================================================================
# Source 3: Vertical Claude Research
# ============================================================================
def source_vertical_claude_research(ai_client, search_terms: list, vertical_name: str) -> list:
    """Use Claude to surface seed-stage companies matching vertical-specific queries.

    IMPORTANT: this function does NOT ask Claude to produce funding figures. Claude
    is unreliable at recalling exact funding amounts and will fabricate plausible-but-wrong
    numbers (e.g. recycling another company's figure). Funding is set to null here and
    populated ONLY by the downstream verification pass (enrich_funding_data), which
    requires a citable source or returns null. Name/description/website are lower-risk
    and acceptable to source here, but are still verified downstream.
    """
    candidates = []
    # Each search term is one Claude call. Cap the fan-out (V21 defines ~24);
    # raise RESEARCH_MAX_QUERIES to use more.
    for term in search_terms[:RESEARCH_MAX_QUERIES]:
        prompt = f"""List up to 5 real, specific seed-stage companies matching: "{term}"

Must be:
- Early-stage (seed or pre-seed), NOT Series A or later
- Founded 2022 or later
- US-based or US-operating
- Real company with named founder and website

DO NOT provide funding amounts — leave those to a separate verification step.
DO NOT guess or estimate any dollar figures.

Format each as JSON on a single line:
{{"name": "...", "description": "...", "website": "...", "industry": "{vertical_name}", "founded_date": "YYYY", "last_funding_round": "seed", "founders": "name, prior background or UNVERIFIED"}}

Do NOT include placeholder or made-up companies. If uncertain about whether a company
is real, skip it entirely. Return ONLY JSON lines, nothing else."""
        try:
            response = ai_client.messages.create(
                model=MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            for line in text.split("\n"):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    c = json.loads(line)
                    nm = str(c.get("name", "")).strip()
                    # Claude annotates some lines ("... - skipping", "not seed")
                    # or invents thin one-word names — drop those here.
                    if (not _plausible_company_name(re.sub(r"\s*\(.*?\)\s*", "", nm))
                            or any(w in nm.lower() for w in ("skip", "not seed", "n/a", "unknown", "example"))
                            or len(nm) < 3):
                        continue
                    # Require a real-looking website — hallucinated companies
                    # usually have a blank or non-domain "website".
                    site = str(c.get("website", "") or "").strip()
                    if not re.match(r"^(https?://)?[a-z0-9-]+\.[a-z]{2,}", site, re.I):
                        continue
                    c["website"] = site if site.startswith("http") else "https://" + site
                    c["name"] = re.sub(r"\s*\(.*?\)\s*$", "", nm)[:80]
                    # Force funding to null/0 so the verification pass MUST populate it.
                    # Never trust a funding figure that came from the sourcing prompt.
                    c["total_funding_usd"] = 0
                    c["_funding_unverified"] = True
                    c.setdefault("hq_city", "")
                    c.setdefault("hq_country", "United States")
                    c.setdefault("headcount", 0)
                    c.setdefault("last_funding_date", "")
                    c.setdefault("linkedin_url", "")
                    c["_source"] = "Claude Vertical Research"
                    candidates.append(c)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            record_llm_error(f"vertical research query '{term}'", e)
    print(f"[Claude Vertical Research] {len(candidates)} candidates")
    return candidates


# ============================================================================
# Source 6: extra early-signal sources (new_sources.py)
# ============================================================================
def _adapt_extra_record(raw: dict, vertical_name: str) -> dict:
    """Map a new_sources.py record onto the full candidate shape.

    Funding is left at 0 / unverified — identical to how YC, SEC and Claude
    Research candidates enter the pipeline; the Step 1b verification pass and the
    post-enrichment size re-check populate and validate the real figure.
    """
    return {
        "name": str(raw.get("name", "")).strip()[:80],
        "website": raw.get("url", ""),
        "description": str(raw.get("description", ""))[:500],
        "industry": vertical_name,
        "hq_city": "",
        "hq_country": "United States",
        "founded_date": "",
        "headcount": 0,
        "total_funding_usd": 0,
        "_funding_unverified": True,
        "last_funding_round": "seed",
        "last_funding_date": "",
        "linkedin_url": "",
        "yc_batch": raw.get("yc_batch", ""),
        "_source": raw.get("source", "extra source"),
    }


def source_extra(vertical: dict) -> list:
    """YC Launches + Product Hunt + VC newsletters, adapted to candidate shape.

    - YC Launch records are dropped if their batch is older than RECENT_YC_BATCHES
      (same recency bar the main YC source applies).
    - VC newsletter feeds are run through source_vertical_rss(), which already
      does "<Company> raises $<N>" headline extraction + seed-stage filtering.
    """
    name = vertical["name"]
    out = []

    yc = [_adapt_extra_record(r, name) for r in source_yc_launches(vertical)]
    yc = [c for c in yc if not c["yc_batch"] or c["yc_batch"] in RECENT_YC_BATCHES]
    print(f"[YC Launches] {len(yc)} candidates")

    ph = [_adapt_extra_record(r, name) for r in source_producthunt(vertical)]
    print(f"[Product Hunt] {len(ph)} candidates")

    nl = source_vertical_rss(VC_NEWSLETTER_FEEDS, name)
    print(f"[VC Newsletters] {len(nl)} candidates")

    out.extend(yc)
    out.extend(ph)
    out.extend(nl)
    return out


# ============================================================================
# Source 7: proprietary scrape layer
# ============================================================================
# The sources above are press-and-announcement based — every fund scraping YC
# and TechCrunch sees the same companies. A vertical's scrape_targets
# (specialist-fund portfolios, accelerator cohorts, program awardee lists,
# market registries) surface companies BEFORE they hit venture press.
#
# Flow: fetch each target's HTML -> reduce to visible text + link list ->
# Claude extracts company names -> passes_scrape_filter() drops rejects ->
# diff against the "Scrape Seen" tab so only NEW names enter the pipeline.
#
# Fetch is static (requests) first; a page that comes back as a JS shell is
# re-fetched with headless Chromium (Playwright) when available. Set
# SCRAPE_HEADLESS=0 to force static-only.

_SCRAPE_UA = "Mozilla/5.0 (compatible; SecondLayerVC-research/1.0; +https://bryanhanleyvc.substack.com)"
SCRAPE_HEADLESS = (os.environ.get("SCRAPE_HEADLESS") or os.environ.get("V21_SCRAPE_HEADLESS") or "1").strip() != "0"
_HEADLESS_STATE = None  # None = untried, True = works, False = unavailable

# Drop non-content blocks (incl. their contents) before extracting text.
# Deliberately conservative — stripping <nav>/<header>/<footer> ate real content
# on sites that nest their listings inside those tags. The extraction prompt is
# told to skip nav/generic text instead.
_TAG_RE = re.compile(r"(?is)<(script|style|noscript|svg|template)\b.*?</\1>")
_ANCHOR_RE = re.compile(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
_STRIP_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    """Reduce raw HTML to visible text + an anchor-text/href list (portfolio
    pages are mostly links), capped for an LLM prompt."""
    html = _TAG_RE.sub(" ", html or "")
    link_lines = []
    for href, inner in _ANCHOR_RE.findall(html):
        t = _WS_RE.sub(" ", _STRIP_RE.sub(" ", inner)).strip()
        if 2 <= len(t) <= 60 and not href.startswith(("#", "mailto:", "javascript:")):
            link_lines.append(f"{t} -> {href}")
    body = _WS_RE.sub(" ", _STRIP_RE.sub(" ", html)).strip()
    combined = body[:5000]
    if link_lines:
        combined += "\n\nLINKS ON PAGE:\n" + "\n".join(link_lines[:150])
    return combined[:9000]


def _static_fetch(url: str, timeout: int) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": _SCRAPE_UA}, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [scrape] static fetch failed: {url} — {e}")
        return ""


def _render_fetch(url: str, nav_timeout_ms: int = 25000) -> str:
    """Render a JS page with headless Chromium (Playwright). Returns raw HTML,
    or '' if Playwright isn't installed or rendering fails. Scrolls to trigger
    lazy-loaded portfolio grids."""
    global _HEADLESS_STATE
    if _HEADLESS_STATE is False:
        return ""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _HEADLESS_STATE = False
        print("  [scrape] playwright not installed — headless fetch disabled for this run")
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(user_agent=_SCRAPE_UA)
            page.set_default_timeout(nav_timeout_ms)
            page.goto(url, wait_until="load")
            for _ in range(4):  # nudge lazy-loaded grids
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(700)
            page.wait_for_timeout(1200)
            html = page.content()
            browser.close()
        _HEADLESS_STATE = True
        return html
    except Exception as e:
        print(f"  [scrape] headless render failed: {url} — {e}")
        return ""


def _fetch_page_text(url: str, timeout: int = 20) -> str:
    """Static fetch first; fall back to headless render when the static result
    is a JS shell (and Playwright is available)."""
    raw = _static_fetch(url, timeout)
    text = _html_to_text(raw) if raw else ""
    if text and not _looks_js_rendered(text):
        return text
    if SCRAPE_HEADLESS:
        rendered = _render_fetch(url)
        if rendered:
            rendered_text = _html_to_text(rendered)
            if len(rendered_text.strip()) > len(text.strip()):
                print(f"  [scrape] headless render used: {url} ({len(rendered_text)} chars)")
                return rendered_text
    return text


_BLOCK_PAGE_RE = re.compile(
    r"(you have been blocked|access denied|ssl handshake failed|attention required|"
    r"enable javascript and cookies|checking your browser|request could not be satisfied|"
    r"this domain (is|may be) for sale|domain for sale)",
    re.I,
)


def _looks_js_rendered(page_text: str) -> bool:
    """A JS SPA that hasn't hydrated yields an almost-empty shell."""
    return len(page_text.strip()) < 250


def _extract_companies_from_page(ai_client, url: str, page_text: str, vertical: dict) -> list:
    """Ask Claude to pull operating-company names out of one scraped page.
    Returns list of {name, website, note}. [] on error or empty page."""
    if len(page_text.strip()) < 250:
        return []
    thesis = vertical.get("second_layer_logic", "")
    kw = ", ".join((vertical.get("keywords") or [])[:12])
    prompt = f"""Text scraped from: {url}

This page is expected to list startups / companies — a VC portfolio, an
accelerator cohort, a government program's awardee or teaming list, or a
market-participant registry.

Extract every entry that is an operating company/startup in or adjacent to
this vertical: "{vertical['name']}".{(' Context: ' + thesis) if thesis else ''}
Relevant terms: {kw}

STRICT RULES:
- Real company names only. Skip nav items, section headers, people's names,
  fund/investor names, report titles, and generic phrases ("Our Portfolio",
  "Learn more", "Read the case study").
- Use ONLY names present in the text below. Do not infer or invent companies.
- For "website": look in the "LINKS ON PAGE" section for a link whose text is
  the company name or whose domain matches it, and return that URL. Never
  return the fund's / this page's own domain. Empty if not found.
- If the page lists no companies, return nothing at all.

Return ONE JSON object per line and nothing else:
{{"name": "...", "website": "https://<company's own domain> or empty", "note": "<=12 words on what they do, or empty", "stage": "pre-seed/seed/series a/… ONLY if the page states it, else empty"}}

--- PAGE TEXT ---
{page_text}"""
    try:
        resp = ai_client.messages.create(
            model=MODEL_EXTRACT, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
    except Exception as e:
        record_llm_error(f"scrape extraction {url}", e)
        return []

    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            c = json.loads(line)
        except json.JSONDecodeError:
            continue
        nm = str(c.get("name", "")).strip()
        # Reject reasoning fragments the extractor sometimes emits as a "name"
        # (e.g. "Diversified Technologies (Frore Systems is not seed — skipping)").
        if not _plausible_company_name(re.sub(r"\s*\(.*?\)\s*", "", nm)) or "skip" in nm.lower():
            continue
        site = str(c.get("website", "") or "").strip()
        if not site.lower().startswith("http"):
            site = ""
        out.append({
            "name": re.sub(r"\s*\(.*?\)\s*$", "", nm)[:80],
            "website": site[:300],
            "note": str(c.get("note", "") or "").strip()[:200],
            "stage": str(c.get("stage", "") or "").strip().lower()[:20],
        })
    return out


def source_vertical_scrape(ai_client, sheet_client, vertical: dict) -> list:
    """Proprietary scrape layer. Returns candidate-shaped dicts for companies
    found on this vertical's scrape_targets that were NOT seen in a prior run.
    No-op (returns []) for any vertical without scrape_targets."""
    targets = get_scrape_targets(vertical)
    if not targets:
        return []

    print(f"[scrape] {len(targets)} targets")
    state = _load_scrape_state(sheet_client)
    blocked = _scrape_blocked(state)  # 'done', or gave up after SCRAPE_RETRY_DAYS
    cache = _load_scrape_cache(sheet_client)  # {url: (hash, [company dicts])}
    first_run = not state
    if first_run:
        print("[scrape] no prior state — first run will record targets without flooding "
              f"the pipeline (cap {SCRAPE_MAX_NEW})")

    new_hits = {}  # norm_name -> (name, website, note, source_url, stage)
    cache_updates = {}
    cached_pages = 0
    for url in targets:
        page_text = _fetch_page_text(url)
        if not page_text or _looks_js_rendered(page_text) or _BLOCK_PAGE_RE.search(page_text[:600]):
            print(f"  [scrape] no usable content (JS shell / blocked / down), skipping: {url}")
            continue
        h = hashlib.md5(page_text.encode("utf-8", "ignore")).hexdigest()
        if cache.get(url, (None,))[0] == h:
            companies = cache[url][1]  # page unchanged — reuse last extraction, no Claude call
            cached_pages += 1
        else:
            companies = _extract_companies_from_page(ai_client, url, page_text, vertical)
            cache_updates[url] = (h, companies)
        for c in companies:
            key = _norm_company(c["name"])
            if not key or key in blocked or key in new_hits:
                continue
            ok, reason = passes_scrape_filter(f"{c['name']} {c.get('note', '')}", vertical)
            if not ok:
                print(f"  [scrape] filtered {c['name']}: {reason}")
                continue
            site = c.get("website", "") or _match_website_from_links(c["name"], page_text)
            new_hits[key] = (c["name"], site, c.get("note", ""), url, c.get("stage", ""))

    if cached_pages:
        print(f"[scrape] {cached_pages} unchanged page(s) reused from cache (no extraction cost)")
    _save_scrape_cache(sheet_client, cache_updates)
    print(f"[scrape] {len(new_hits)} new companies after dedup + filter")

    selected = list(new_hits.values())[:SCRAPE_MAX_NEW]
    if len(new_hits) > SCRAPE_MAX_NEW:
        print(f"[scrape] capping at {SCRAPE_MAX_NEW}; remaining will surface next run")

    # Record new names as 'pending'. Only companies that later get WRITTEN or
    # HARD-rejected (over the funding cap / too old) become 'done' — a company
    # that just scored 55% on thin data re-surfaces next run (main() resolves
    # this after scoring; _scrape_blocked() also gives up after SCRAPE_RETRY_DAYS).
    _record_scrape_seen(sheet_client, [
        (n, u, note) for (n, _w, note, u, _s) in selected if _norm_company(n) not in state
    ])

    out = []
    for (n, w, note, u, stage) in selected:
        rec = _adapt_extra_record(
            # website: the company's OWN site if the extractor found one — never
            # the fund/portfolio page (u), which would send contact-enrichment to
            # the fund's inbox.
            {"name": n, "url": w if w and not _same_host(w, u) else "",
             "description": note, "source": "Scrape"},
            vertical["name"],
        )
        rec["_scrape_source_url"] = u
        rec["_from_scrape"] = True
        if stage:  # portfolio pages often label the round — trust it over the default
            rec["last_funding_round"] = stage
        out.append(rec)
    return out


def _match_website_from_links(name: str, page_text: str) -> str:
    """Pull the company's own URL from the page's 'LINKS ON PAGE' section
    ('CompanyName -> https://…') when the extractor didn't return one."""
    if "LINKS ON PAGE:" not in page_text:
        return ""
    nkey = _norm_company(name)
    if not nkey:
        return ""
    for ln in page_text.split("LINKS ON PAGE:", 1)[1].splitlines():
        if " -> " not in ln:
            continue
        text, _, href = ln.partition(" -> ")
        href = href.strip()
        if not href.lower().startswith("http"):
            continue
        host = href.split("//", 1)[-1].split("/", 1)[0].lower().removeprefix("www.")
        # link text matches the company, or the domain contains the name
        if _norm_company(text) == nkey or nkey.replace(" ", "") in host.replace("-", "").replace(".", ""):
            # skip links back to the fund/aggregator itself
            if not any(s in host for s in ("linkedin", "twitter", "crunchbase", "youtube", "medium")):
                return href
    return ""


def _same_host(a: str, b: str) -> bool:
    from urllib.parse import urlparse
    try:
        ha = urlparse(a).netloc.lower().removeprefix("www.")
        hb = urlparse(b).netloc.lower().removeprefix("www.")
        return bool(ha) and ha == hb
    except Exception:
        return False


_SCRAPE_STATE_HEADERS = ["Company", "First Seen", "Source URL", "Note", "Status"]
_SCRAPE_CACHE_TAB = "Scrape Cache"


def _scrape_state_tab(sheet_client):
    """Get the Scrape Seen tab, migrating a pre-Status (4-column) tab in place."""
    tab = ensure_tab(sheet_client, SCRAPE_STATE_TAB,
                     headers=_SCRAPE_STATE_HEADERS, rows=5000, cols=6)
    try:
        if tab.col_count < len(_SCRAPE_STATE_HEADERS):
            tab.resize(rows=max(tab.row_count, 5000), cols=len(_SCRAPE_STATE_HEADERS) + 1)
        if (tab.row_values(1) or [])[:5] != _SCRAPE_STATE_HEADERS:
            tab.update(range_name="A1:E1", values=[_SCRAPE_STATE_HEADERS])
    except Exception as e:
        print(f"[scrape] Scrape Seen migration warning: {e}")
    return tab


def _load_scrape_cache(sheet_client) -> dict:
    """{url: (content_hash, [company dict, …])} — lets an unchanged portfolio
    page skip its Claude extraction call entirely."""
    try:
        tab = sheet_client.open_by_key(SHEET_ID).worksheet(_SCRAPE_CACHE_TAB)
        rows = tab.get_all_records()
    except Exception:
        return {}
    out = {}
    for r in rows:
        url = str(r.get("URL", "")).strip()
        if not url:
            continue
        try:
            companies = json.loads(r.get("Companies") or "[]")
        except (json.JSONDecodeError, TypeError):
            companies = []
        out[url] = (str(r.get("Hash", "")).strip(), companies)
    return out


def _save_scrape_cache(sheet_client, updates: dict) -> None:
    """updates: {url: (hash, [company dicts])}. Rewrites the whole small tab."""
    if not updates:
        return
    try:
        tab = ensure_tab(sheet_client, _SCRAPE_CACHE_TAB,
                         headers=["URL", "Hash", "Companies", "Updated"], rows=200, cols=4)
        existing = {str(r.get("URL", "")).strip(): r for r in tab.get_all_records()}
        for url, (h, companies) in updates.items():
            existing[url] = {"URL": url, "Hash": h,
                             "Companies": json.dumps(companies)[:45000],
                             "Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        tab.clear()
        tab.append_row(["URL", "Hash", "Companies", "Updated"])
        tab.append_rows([[r["URL"], r["Hash"], r["Companies"], r["Updated"]] for r in existing.values()])
    except Exception as e:
        print(f"[scrape] could not update '{_SCRAPE_CACHE_TAB}': {e}")


def _load_scrape_state(sheet_client) -> dict:
    """{norm_name: {status, first_seen, row}} from the Scrape Seen tab."""
    try:
        tab = sheet_client.open_by_key(SHEET_ID).worksheet(SCRAPE_STATE_TAB)
        rows = tab.get_all_records()
    except Exception:
        return {}
    out = {}
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        nm = str(r.get("Company", "")).strip()
        if nm:
            out[_norm_company(nm)] = {
                "status": str(r.get("Status", "") or "pending").strip().lower(),
                "first_seen": str(r.get("First Seen", "") or ""),
                "row": i,
            }
    return out


def _scrape_blocked(state: dict) -> set:
    """Names to skip: resolved ('done'), or 'pending' past the retry window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SCRAPE_RETRY_DAYS)).strftime("%Y-%m-%d")
    blocked = set()
    for norm, s in state.items():
        if s["status"] == "done" or (s["first_seen"] and s["first_seen"] < cutoff):
            blocked.add(norm)
    return blocked


def _record_scrape_seen(sheet_client, rows: list) -> None:
    """Append new (name, source_url, note) rows with Status='pending'."""
    if not rows:
        return
    try:
        tab = _scrape_state_tab(sheet_client)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tab.append_rows([[n, now, u, note, "pending"] for (n, u, note) in rows])
        print(f"[scrape] recorded {len(rows)} new names to '{SCRAPE_STATE_TAB}'")
    except Exception as e:
        print(f"[scrape] could not update '{SCRAPE_STATE_TAB}': {e}")


def _resolve_scrape_seen(sheet_client, state: dict, done_norms: set) -> None:
    """Mark rows 'done' for scrape companies that reached a terminal outcome
    (written to the sheet, or hard-rejected). Everything else stays 'pending'."""
    updates = [
        {"range": f"E{state[n]['row']}", "values": [["done"]]}
        for n in done_norms
        if n in state and state[n]["status"] != "done"
    ]
    if not updates:
        return
    try:
        _scrape_state_tab(sheet_client).batch_update(updates)
        print(f"[scrape] resolved {len(updates)} names to 'done' in '{SCRAPE_STATE_TAB}'")
    except Exception as e:
        print(f"[scrape] could not resolve '{SCRAPE_STATE_TAB}': {e}")


# ============================================================================
# Funding verification for $0-funding candidates (YC + RSS fallbacks)
# ============================================================================
def _crunchbase_lookup(company_name: str) -> dict:
    """
    Try to fetch funding data from Crunchbase Basic API.
    Returns dict with total_funding_usd, last_funding_type, last_funding_date, founded_year.
    Returns empty dict on any failure (no API key, no result, error).

    Requires CRUNCHBASE_API_KEY env var. Free tier allows limited monthly calls.
    Skip silently if no key configured — pipeline still works without it.
    """
    api_key = os.environ.get("CRUNCHBASE_API_KEY")
    if not api_key:
        return {}
    try:
        url = "https://api.crunchbase.com/api/v4/searches/organizations"
        headers = {"X-cb-user-key": api_key, "Content-Type": "application/json"}
        payload = {
            "field_ids": ["identifier", "funding_total", "last_funding_type",
                          "last_funding_at", "founded_on"],
            "query": [{"type": "predicate", "field_id": "identifier",
                       "operator_id": "contains", "values": [company_name]}],
            "limit": 1,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            return {}
        entities = resp.json().get("entities", [])
        if not entities:
            return {}
        props = entities[0].get("properties", {})
        return {
            "total_funding_usd": (props.get("funding_total") or {}).get("value_usd"),
            "last_funding_type": props.get("last_funding_type"),
            "last_funding_date": (props.get("last_funding_at") or {}).get("value"),
            "founded_year": ((props.get("founded_on") or {}).get("value") or "")[:4],
            "_source": "Crunchbase",
        }
    except Exception:
        return {}


# --- SEC EDGAR Form D funding lookup (free, no key, strict name match) --------
_SEC_UA = {"User-Agent": "SecondLayerVC research bryanhanleyvc@gmail.com"}
_LEGAL_SUFFIX_RE = re.compile(
    r"[\s,.]+(inc|incorporated|llc|l\.l\.c|corp|corporation|co|ltd|limited|lp|l\.p|plc|holdings)\.?$",
    re.I,
)
# Names that mean "investment vehicle / holding entity", not "operating startup".
# Filters both the SEC Form D source and the funding-verification lookup.
_FUND_ENTITY_RE = re.compile(
    r"\b(spv|fund|feeder|sicav|reit|dst|s\.?c\.?sp|investments?|activist|ventures?|"
    r"partners|capital|holdings|trust|advis[eo]rs?|management|co[- ]?invest(?:ment)?s?|"
    r"offshore|series)\b|\bl\.?\s?p\.?\b",
    re.I,
)


def _norm_company(name: str) -> str:
    n = (name or "").lower().strip()
    n = re.sub(r"\(cik.*?\)", "", n)
    prev = None
    while prev != n:  # strip stacked suffixes ("Foo Co, Inc.")
        prev = n
        n = _LEGAL_SUFFIX_RE.sub("", n).strip()
    return re.sub(r"[^a-z0-9 ]", "", n).strip()


# Form D <industryGroupType> values that mean "not an operating tech startup".
_SEC_NONSTARTUP_INDUSTRY = re.compile(
    r"pooled investment|real estate|reit|oil (and|&) gas|mining|agriculture|"
    r"commercial banking|insurance|other banking|other real estate",
    re.I,
)
# Above this, a Form D figure is not a seed signal — treat as unverified.
_SEC_SANE_MAX = 60_000_000


def _sec_form_d_lookup(company_name: str, max_filings: int = 6) -> dict:
    """Look up a company's own Form D filings on EDGAR.

    Uses the MOST RECENT filing's totalAmountSold (not a sum across years —
    infra companies file many Form Ds for project debt, which summed to "$5.5B").
    Rejects fund/SPV names, non-startup <industryGroupType>, and figures over
    $60M (not a seed signal). Returns {} on no confident match.
    """
    q = _norm_company(company_name)
    if len(q) < 4:
        return {}
    try:
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": f'"{company_name}"', "forms": "D"},
            headers=_SEC_UA, timeout=20,
        )
        hits = r.json().get("hits", {}).get("hits", []) if r.status_code == 200 else []
    except Exception:
        return {}

    matched = []
    for h in hits:
        src = h.get("_source", {})
        display = (src.get("display_names") or [""])[0]
        if _FUND_ENTITY_RE.search(display):
            continue
        norm = _norm_company(display)
        if norm == q or (len(q.split()) >= 2 and norm.startswith(q + " ")):
            matched.append((h.get("_id", ""), (src.get("ciks") or [""])[0], src.get("file_date", ""), display))
    if not matched:
        return {}

    # newest filing first; a company whose most recent Form D is >5 years old is
    # defunct or a wrong name match ("Conductor" -> a 2009 filing).
    matched.sort(key=lambda t: t[2] or "", reverse=True)
    newest = matched[0][2] or ""
    if newest and newest < (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d"):
        return {}
    for _id, cik, fdate, display in matched[:max_filings]:
        if not cik or ":" not in _id:
            continue
        acc = _id.split(":")[0].replace("-", "")
        try:
            xml = requests.get(
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/primary_doc.xml",
                headers=_SEC_UA, timeout=20,
            ).text
        except Exception:
            continue
        time.sleep(0.2)  # SEC politeness

        ig = re.search(r"<industryGroupType>([^<]+)</industryGroupType>", xml)
        if ig and _SEC_NONSTARTUP_INDUSTRY.search(ig.group(1)):
            return {}  # a fund / REIT / oil&gas entity slipped the name filter
        m = re.search(r"<totalAmountSold>(\d+)</totalAmountSold>", xml)
        if not m:
            continue
        amount = float(m.group(1))
        if amount <= 0 or amount > _SEC_SANE_MAX:
            return {}  # not a seed-scale figure — don't trust it
        cik0 = int(cik)
        return {
            "total_funding_usd": int(amount),
            "last_funding_date": fdate or "",
            "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik0:010d}&type=D",
            "entity_name": re.sub(r"\s*\(CIK.*?\)", "", display).strip(),
            "n_filings": len(matched),
        }
    return {}


def verify_zero_funding(ai_client, candidates: list) -> None:
    """
    Multi-pass funding verification for $0 candidates. Never guesses — a figure
    is set only when a source can be named.

      1.  Crunchbase API (only if CRUNCHBASE_API_KEY is set)
      1b. SEC EDGAR Form D — the company's own filings, strict name match
      2.  Claude, with a hard source-citation requirement

    Every candidate that starts at $0 gets a `_funding_checks` list recording
    what each pass found ("crunchbase: no key", "sec form d: $2.1M (2024-03-01)",
    "claude: no citable source"). Sets total_funding_usd, last_funding_round,
    last_funding_date, founded_year, _funding_confidence, _funding_source (a
    URL/citation when verified, else the joined checks), _funding_unverified.
    """
    zero = [c for c in candidates if safe_float(c.get("total_funding_usd", 0)) == 0]
    if not zero:
        return
    for c in zero:
        c.setdefault("_funding_checks", [])

    have_cb_key = bool(os.environ.get("CRUNCHBASE_API_KEY"))

    # ----- Pass 1: Crunchbase lookup -----
    crunchbase_hits = 0
    still_unknown = []
    for c in zero:
        cb_data = _crunchbase_lookup(c["name"]) if have_cb_key else {}
        if cb_data and cb_data.get("total_funding_usd"):
            c["total_funding_usd"] = cb_data["total_funding_usd"]
            c["last_funding_round"] = cb_data.get("last_funding_type") or c.get("last_funding_round", "")
            c["last_round_type"] = cb_data.get("last_funding_type") or ""
            c["last_funding_date"] = cb_data.get("last_funding_date") or c.get("last_funding_date", "")
            c["founded_year"] = cb_data.get("founded_year") or c.get("founded_year", "")
            c["_funding_confidence"] = "high"
            c["_funding_source"] = "https://www.crunchbase.com/ (Crunchbase API)"
            c["_funding_unverified"] = False
            c["_funding_checks"].append(f"crunchbase: ${cb_data['total_funding_usd']:,.0f}")
            crunchbase_hits += 1
        else:
            c["_funding_checks"].append("crunchbase: no API key" if not have_cb_key else "crunchbase: no match")
            still_unknown.append(c)
    if crunchbase_hits:
        print(f"[Funding verify] Crunchbase: {crunchbase_hits} verified")

    # ----- Pass 1b: SEC EDGAR Form D (free, strict match) -----
    sec_hits = 0
    after_sec = []
    for c in still_unknown:
        sec = _sec_form_d_lookup(c["name"])
        if sec:
            c["total_funding_usd"] = sec["total_funding_usd"]
            c["last_funding_date"] = sec.get("last_funding_date") or c.get("last_funding_date", "")
            c["_funding_confidence"] = "medium"
            c["_funding_source"] = sec["source_url"]
            c["_funding_unverified"] = False
            c["_funding_checks"].append(
                f"sec form d: ${sec['total_funding_usd']:,.0f} over {sec['n_filings']} filing(s), "
                f"as {sec['entity_name']}"
            )
            sec_hits += 1
        else:
            c["_funding_checks"].append("sec form d: no matching filing")
            after_sec.append(c)
        time.sleep(0.15)
    still_unknown = after_sec
    if sec_hits:
        print(f"[Funding verify] SEC Form D: {sec_hits} verified")

    # ----- Pass 1c: the company's own site ("we raised $Xm seed round") -----
    site_hits = 0
    after_site = []
    for c in still_unknown:
        site = str(c.get("website", "") or "")
        fx = scan_site_for_funding(site) if site else {}
        if fx:
            c["total_funding_usd"] = fx["amount_usd"]
            c["_funding_confidence"] = "medium"
            c["_funding_source"] = fx["source_url"]
            c["_funding_unverified"] = False
            if fx.get("round_type"):
                c["last_funding_round"] = fx["round_type"]
            c["_funding_checks"].append(f"company site: ${fx['amount_usd']:,.0f} — {fx['source_url']}")
            site_hits += 1
        else:
            after_site.append(c)
    still_unknown = after_site
    if site_hits:
        print(f"[Funding verify] Company site: {site_hits} verified")

    if not still_unknown:
        return

    # ----- Pass 2: Claude verification, chunked (a single 40-company call at
    # max_tokens=2000 truncated its own JSON and lost the whole batch) -----
    total_updated = total_unverified = 0
    for i in range(0, len(still_unknown), 10):
        chunk = still_unknown[i:i + 10]
        u, n = _claude_verify_chunk(ai_client, chunk)
        total_updated += u
        total_unverified += n
    print(f"[Funding verify] Claude: {total_updated} verified, {total_unverified} unverified")

    _finalize_unverified(still_unknown)


def _claude_verify_chunk(ai_client, chunk: list) -> tuple:
    """Verify one small batch. Slim response (no founders array — score_candidate
    handles founders) so the JSON never truncates. Returns (updated, unverified)."""
    names = [c["name"] for c in chunk]
    prompt = f"""Verify the most recent funding round for each seed-stage startup below.
DO NOT estimate, extrapolate, or use vague general knowledge. Return a figure
ONLY if you can name a specific source (press release, SEC filing, Crunchbase,
the company's own site). Otherwise null.

For each company return JSON:
{{"total_funding_usd": int or null, "last_round_type": "Pre-seed/Seed/Series A/Grant/…" or null,
  "last_funding_date": "YYYY-MM-DD" or null, "founded_year": "YYYY" or null,
  "source_citation": "URL or specific reference" or null,
  "confidence": "high" | "medium" | "low" | "unverified"}}

If confidence is "low" or "unverified", total_funding_usd MUST be null.

Companies: {json.dumps(names)}

Return ONLY a JSON object mapping each company name to its fields. No preamble."""
    try:
        resp = ai_client.messages.create(
            model=MODEL, max_tokens=1600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        text = text[text.find("{"):text.rfind("}") + 1] if "{" in text else text
        verified = json.loads(text)
    except Exception as e:
        record_llm_error(f"funding verification chunk ({names[0]}…)", e)
        for c in chunk:
            c["_funding_checks"].append("claude: verification errored")
        return 0, len(chunk)

    updated = unverified = 0
    for c in chunk:
        info = verified.get(c["name"]) or {}
        conf = (info.get("confidence") or "").lower()
        amt = info.get("total_funding_usd")
        if not info or conf in ("low", "unverified") or amt is None:
            c["_funding_confidence"] = conf or "unverified"
            c["_funding_checks"].append("claude: no citable source")
            unverified += 1
            continue
        c["total_funding_usd"] = amt
        c["_funding_unverified"] = False
        c["_funding_confidence"] = conf or "medium"
        c["_funding_source"] = info.get("source_citation") or "Claude verified"
        c["_funding_checks"].append(f"claude: ${amt:,.0f} — {info.get('source_citation') or 'cited'}")
        if info.get("last_round_type"):
            c["last_funding_round"] = info["last_round_type"]
        if info.get("last_funding_date"):
            c["last_funding_date"] = info["last_funding_date"]
        if info.get("founded_year"):
            c["founded_year"] = info["founded_year"]
        updated += 1
    return updated, unverified


def _finalize_unverified(candidates: list) -> None:
    """For any candidate still at $0 after all passes, make the state legible:
    _funding_source becomes the joined audit trail so the sheet/digest can show
    exactly what was tried."""
    for c in candidates:
        if safe_float(c.get("total_funding_usd", 0)) == 0:
            c["_funding_unverified"] = True
            c.setdefault("_funding_confidence", "unverified")
            checks = c.get("_funding_checks") or []
            c["_funding_source"] = ("tried — " + "; ".join(checks)) if checks else "no verification attempted"


# ============================================================================
# Dedup
# ============================================================================
def deduplicate(candidates: list, existing_names: set) -> list:
    """Dedup on the normalized company name (strips Inc/LLC/punctuation) so
    'Pearl Street' / 'Pearl Street Technologies, Inc.' collapse to one."""
    seen = {_norm_company(n) for n in existing_names if n}
    unique = []
    for c in candidates:
        raw = str(c.get("name", "")).strip()
        key = _norm_company(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


# ============================================================================
# Main
# ============================================================================
def evaluate_consumer_second_layer_fit(ai_client, candidate: dict):
    """
    Consumer-specific Second Layer evaluator for V20 (Consumer Health & Wellness Brands).
    Same 1-3 scoring scale as the B2B version, but reframes Second Layer logic for consumer.

    Consumer Second Layer = the company offers a better-for-you alternative in a legacy
    indulgence/consumer category where dominant trends (AI-enabled health awareness, wellness
    movement, functional ingredient adoption) have shifted consumer demand faster than
    incumbents can serve it.

    Examples:
      - Dominant trend: AI-driven health awareness + wellness movement
        Second Layer: functional protein chocolate (DEFI Snacks) disrupting $22B chocolate category
      - Dominant trend: sober-curious movement
        Second Layer: non-alcoholic adaptogen apéritifs (De Soi)
      - FAILS: another energy drink, another protein bar, another supplement — categories
        already commoditized rather than truly shifted by the trend
    """
    prompt = f"""Evaluate consumer Second Layer fit for this brand.

CONSUMER SECOND LAYER = the brand offers a better-for-you / cleaner-label / functional
alternative in a legacy indulgence category (snacking, beverages, personal care, household)
where consumer demand has shifted faster than incumbents can serve it.

The dominant trend is: AI-driven health awareness + wellness movement + functional ingredient
adoption. Better-for-you consumer products are the Second Layer response.

Strong consumer Second Layer examples:
- DEFI Snacks (functional protein chocolate disrupting $22B chocolate category)
- OLIPOP (prebiotic soda displacing legacy soda)
- De Soi (NA adaptogen apéritifs in the sober-curious movement)
- Hanni (clean personal care for underserved demographics)

FAILS Second Layer (commodity, not shifted):
- Another generic protein bar, energy drink, or supplement in already-commoditized categories
- A traditional CPG brand without a functional / clean-label / category-disruption angle
- B2B SaaS or infrastructure (this is a consumer vertical — should not appear here)

Rate 1-3:
1 = Fails (commodity product, no category-shift logic, or wrong category entirely)
2 = Borderline (some functional/clean-label angle but unclear differentiation)
3 = Strong consumer Second Layer fit (genuine category disruption with proven trend tailwind)

Company: {candidate.get("name", "")}
Description: {str(candidate.get("description", ""))[:500]}

Return ONLY: SCORE: N | REASON: one short sentence"""
    try:
        resp = ai_client.messages.create(
            model=MODEL, max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        score = 2
        reason = ""
        for line in text.replace("|", "\n").split("\n"):
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                try:
                    score = int(line.split(":", 1)[1].strip()[0])
                except Exception:
                    pass
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        return max(1, min(3, score)), reason or "consumer eval no reason"
    except Exception as e:
        record_llm_error(f"consumer Second Layer eval for {candidate.get('name')}", e)
        # Fail CLOSED — score < 2 excludes the candidate downstream.
        return 1, "consumer Second Layer eval failed (LLM error) — excluded"


def _funding_line(cand: dict) -> str:
    val = safe_float(cand.get("total_funding_usd", 0))
    conf = (cand.get("_funding_confidence") or "").lower()
    src = str(cand.get("_funding_source") or "").strip()
    # Surface any confirm-step flag (CONFLICT / STAGE_MISMATCH / STALE).
    flags = [c.split("—", 1)[-1].strip() for c in (cand.get("_funding_checks") or [])
             if str(c).startswith("confirm:")]
    warn = f"  [!] {'; '.join(flags)}" if flags else ""
    if cand.get("_funding_unverified") or conf in ("", "low", "unverified") or val == 0:
        src = src[len("tried — "):] if src.startswith("tried — ") else src
        return (f"unverified (checked {src})" if src else "unverified") + warn
    date = cand.get("last_funding_date") or ""
    tag = " (single source)" if conf == "medium" else ""
    return f"${val:,.0f}{(' as of ' + date) if date else ''}{tag} — {src}" + warn


def build_outreach_digest(scored: list) -> str:
    """Plain-text digest of the top candidates with outreach details, for the
    email to the analyst. `scored` is expected pre-sorted (best first); items
    may carry a "contact" dict from enrich_contact()."""
    lines = [f"{len(scored)} candidate(s) scored above threshold. Top {min(DIGEST_TOP_N, len(scored))} for outreach:\n"]
    for i, c in enumerate(scored[:DIGEST_TOP_N], 1):
        cand = c["candidate"]
        contact = c.get("contact") or {}
        lines.append(f"{i}. {cand.get('name', '?')}  —  {c['weighted_pct']}%  {c['decision']}")
        if c.get("summary"):
            lines.append(f"   {c['summary']}")
        if c.get("founders"):
            lines.append(f"   Founders: {c['founders']}")
        lines.append(f"   Second Layer: {c.get('sl_reason', '')}")
        lines.append(f"   Funding: {_funding_line(cand)}")
        if c.get("strengths"):
            lines.append(f"   + {c['strengths']}")
        if c.get("risks"):
            lines.append(f"   - {c['risks']}")
        website = contact.get("website") or cand.get("website") or "—"
        email = contact.get("email") or "—"
        linkedin = contact.get("linkedin") or cand.get("linkedin_url") or "—"
        lines.append(f"   Website:  {website}")
        lines.append(f"   Email:    {email}   ({contact.get('note', 'not looked up')})")
        lines.append(f"   LinkedIn: {linkedin}")
        lines.append("")
    if len(scored) > DIGEST_TOP_N:
        lines.append(f"(+{len(scored) - DIGEST_TOP_N} more in the sheet)")
    return "\n".join(lines)


def main():
    ai_client = get_anthropic_client()
    industry_query = os.environ.get("INDUSTRY_QUERY", "").strip()
    override = os.environ.get("VERTICAL_INDEX", "").strip()

    if industry_query:
        # On-demand: synthesize a vertical from a free-text industry string.
        print(f"Synthesizing vertical from industry query: {industry_query!r}")
        vertical = synthesize_vertical(ai_client, industry_query, MODEL)
        idx = "custom"
        target_tab = ON_DEMAND_TAB
        print(f"  -> {vertical['name']}: {len(vertical['keywords'])} keywords, "
              f"{len(vertical['rss_feeds'])} valid feeds, {len(vertical['search_terms'])} search terms")
    elif override:
        try:
            idx = int(override)
        except ValueError:
            raise RuntimeError(f"Invalid VERTICAL_INDEX: {override}")
        vertical = get_vertical(idx)
        target_tab = VERTICAL_TAB
    else:
        idx, vertical = get_vertical_by_day_of_year()
        target_tab = VERTICAL_TAB

    name = vertical["name"]
    keywords = vertical.get("keywords", [])
    rss_feeds = vertical.get("rss_feeds", [])
    search_terms = vertical.get("search_terms", [])

    label = f"V{idx}" if isinstance(idx, int) else "on-demand"
    print(f"\n{'='*60}")
    print(f"Vertical Pipeline — {label}: {name}  ->  '{target_tab}' tab")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    sheet_client = get_sheet_client()

    # Step 1: Source collection
    print("STEP 1: Pulling from vertical-specific sources")
    print("-" * 60)
    candidates = []
    candidates.extend(source_vertical_yc(keywords, name))
    candidates.extend(source_sec_form_d(keywords, name))
    candidates.extend(source_techcrunch(keywords, name))
    candidates.extend(source_vertical_rss(rss_feeds, name))
    candidates.extend(source_vertical_claude_research(ai_client, search_terms, name))
    if EXTRA_SOURCES_ENABLED:
        candidates.extend(source_extra(vertical))
    else:
        print("[extra sources] skipped (EXTRA_SOURCES=0)")
    if SCRAPE_LAYER_ENABLED:
        candidates.extend(source_vertical_scrape(ai_client, sheet_client, vertical))
    elif get_scrape_targets(vertical):
        print("[scrape] skipped (SCRAPE_LAYER=0)")
    print(f"\nTotal raw: {len(candidates)}")

    # Step 1a: Dedup FIRST — don't spend funding-verification / scoring calls on
    # the same company sourced 2-3 ways.
    existing = read_existing_names(sheet_client, target_tab)
    candidates = deduplicate(candidates, existing)
    print(f"After dedup: {len(candidates)}")

    # Step 1b: Verify funding for $0 candidates before gating
    print("\nSTEP 1b: Verifying zero-funding candidates")
    print("-" * 60)
    verify_zero_funding(ai_client, candidates)
    # Enrichment writes the founding year to `founded_year`; the age gate and the
    # scorer read `founded_date`. Fold it over so the enriched value is used.
    for c in candidates:
        if not c.get("founded_date") and c.get("founded_year"):
            c["founded_date"] = str(c["founded_year"])

    # Step 1c: Confirm funding figures are internally consistent (cross-source
    # agreement, stage/amount plausibility, staleness). Downgrades or clears
    # figures that don't hold up — no bad number should reach the sheet clean.
    print("\nSTEP 1c: Confirming funding reports")
    print("-" * 60)
    _fc = {}
    for c in candidates:
        verdict, note = confirm_funding_report(c)
        if verdict != "OK":
            _fc[verdict] = _fc.get(verdict, 0) + 1
            print(f"  {verdict}: {c.get('name', '?')} — {note}")
    print(f"Confirmed: {len(candidates) - sum(_fc.values())} clean, " +
          (", ".join(f"{n}×{v}" for v, n in _fc.items()) if _fc else "0 flagged"))

    # Step 3: Three hard gates
    print(f"\nSTEP 2: Three hard gates")
    print("-" * 60)
    passed, scrape_done = [], set()  # scrape_done: names not worth retrying
    for c in candidates:
        ok, reason = passes_all_gates(c)
        if ok:
            passed.append(c)
        elif c.get("_from_scrape") and ("exceeds" in reason or "years old" in reason or "Series A" in reason):
            scrape_done.add(_norm_company(c.get("name", "")))  # over cap / too old — won't change
    print(f"Passed gates: {len(passed)} / {len(candidates)}")

    # Step 3b: Post-enrichment SIZE re-verification.
    # The hard funding gate runs on pre-enrichment data and passes companies with
    # missing funding on their stage LABEL alone. Now that verify_zero_funding has
    # populated real figures, re-check size and REMOVE any company whose verified
    # funding actually exceeds the $10M cap (the Emerald AI / Gridware leak).
    # Companies that survive are tagged with a size status for visibility.
    print(f"\nSTEP 2b: Post-enrichment size verification")
    print("-" * 60)
    size_verified = []
    for c in passed:
        status, reason = verify_size_post_enrichment(c)
        c["_size_status"] = status
        if status == "REJECT":
            print(f"  REMOVED: {c.get('name', '?')} — {reason}")
            if c.get("_from_scrape"):
                scrape_done.add(_norm_company(c.get("name", "")))
            continue
        if status in ("ABOVE_RANGE", "UNVERIFIED"):
            print(f"  FLAG ({status}): {c.get('name', '?')} — {reason}")
        size_verified.append(c)
    passed = size_verified
    print(f"After size verification: {len(passed)}")

    # Step 4: Second Layer thesis filter
    # V20 (Consumer Health & Wellness Brands) uses a different logic than B2B verticals.
    # Consumer brands don't solve infrastructure problems — they offer alternatives in
    # categories where consumer awareness has shifted (e.g. health/wellness trend creates
    # demand for better-for-you alternatives in legacy indulgence categories).
    # Set SKIP_SECOND_LAYER_FOR_V20 = True to bypass the filter entirely for consumer.
    SKIP_SECOND_LAYER_FOR_V20 = False  # change to True to skip filter for V20 entirely
    print(f"\nSTEP 3: Second Layer filter")
    print("-" * 60)
    passed_sl = []
    is_consumer_vertical = (idx == 20)
    if is_consumer_vertical and SKIP_SECOND_LAYER_FOR_V20:
        print("Vertical 20 (Consumer): skipping Second Layer filter entirely")
        for c in passed:
            c["_sl_reason"] = "Consumer vertical — filter skipped, see vertical-specific thesis"
            passed_sl.append(c)
    else:
        for c in passed:
            if is_consumer_vertical:
                sl_score, sl_reason = evaluate_consumer_second_layer_fit(ai_client, c)
            else:
                sl_score, sl_reason = evaluate_second_layer_fit(ai_client, c)
            if sl_score < 2:
                continue
            c["_sl_reason"] = sl_reason
            passed_sl.append(c)
    print(f"Passed Second Layer: {len(passed_sl)}")

    # Step 3b: Enrich the Second Layer survivors with their own website text
    # before scoring — a one-line blurb can't clear the threshold.
    if passed_sl:
        print("\nSTEP 3b: Fetching website context for scoring")
        print("-" * 60)
        for c in passed_sl:
            site = c.get("website") or ""
            c["_site_text"] = fetch_company_context(site) if site else ""
            print(f"  {c.get('name', '?'):30s} {len(c['_site_text'])} chars from site")

    # Step 5: 9-factor scoring
    print(f"\nSTEP 4: 9-factor scoring")
    print("-" * 60)
    scored, below = [], []
    for c in passed_sl:
        result = score_candidate(ai_client, c, c["_sl_reason"])
        pct = result["weighted_pct"]
        rec = {"candidate": c, "sl_reason": c["_sl_reason"], **result,
               "decision": decision_from_score(pct)}
        if pct < MIN_SCORE_PCT:
            below.append(rec)
            print(f"  {c['name']:33s} {pct:5.1f}%  (below {MIN_SCORE_PCT}) [{c.get('_source', '?')}]")
            continue
        scored.append(rec)
        print(f"  {c['name']:33s} {pct:5.1f}%  {rec['decision']} [{c.get('_source', '?')}]")

    scored.sort(key=lambda x: x["weighted_pct"], reverse=True)
    print(f"\nScored above threshold ({MIN_SCORE_PCT}%): {len(scored)}  |  below: {len(below)}")

    # Step 5b: Contact enrichment for the top slice (website scrape only).
    if scored and ENRICH_CONTACTS:
        print(f"\nSTEP 5b: Contact lookup for top {min(DIGEST_TOP_N, len(scored))}")
        print("-" * 60)
        for c in scored[:DIGEST_TOP_N]:
            info = enrich_contact(c["candidate"])
            c["contact"] = info
            # Fold enriched website/LinkedIn back onto the candidate so the sheet gets them.
            if info.get("website"):
                c["candidate"]["website"] = info["website"]
            if info.get("linkedin") and not c["candidate"].get("linkedin_url"):
                c["candidate"]["linkedin_url"] = info["linkedin"]
            print(f"  {c['candidate']['name']:30s} email={info.get('email') or '—':30s} {info.get('note','')}")

    # Step 6: Write
    print(f"\nSTEP 5: Writing to '{target_tab}' tab")
    print("-" * 60)
    write_scored_candidates(sheet_client, target_tab, scored, vertical_label=name)

    # Resolve scrape state: written or hard-rejected -> 'done'; the rest stay
    # 'pending' and re-surface next run (until SCRAPE_RETRY_DAYS).
    if SCRAPE_LAYER_ENABLED and get_scrape_targets(vertical):
        for s in scored:
            if s["candidate"].get("_from_scrape"):
                scrape_done.add(_norm_company(s["candidate"].get("name", "")))
        _resolve_scrape_seen(sheet_client, _load_scrape_state(sheet_client), scrape_done)

    # Step 7: Email digest
    if scored:
        if industry_query:
            subject = f"On-Demand Pipeline: {name} — {len(scored)} candidates"
            header = f"Industry query: {industry_query}\nSynthesized vertical: {name}\n"
        else:
            subject = f"Vertical Pipeline {name} — {len(scored)} candidates"
            header = f"Vertical: {name}\n"
        send_email_digest(subject=subject, body=header + "\n" + build_outreach_digest(scored))

    print(f"\n{'='*60}")
    print(f"Pipeline run complete — {label}: {name}")
    print(f"{'='*60}\n")

    # Surface any swallowed LLM failures loudly. A run that "completes" while a
    # chunk of its scoring/eval calls errored is not a healthy run — say so, and
    # exit non-zero if the failures were widespread so the workflow shows red.
    errors = llm_error_count()
    if errors:
        print("!" * 60, file=sys.stderr)
        print(llm_error_summary(), file=sys.stderr)
        print("!" * 60, file=sys.stderr)
        if scored is not None and errors >= max(5, len(scored)):
            raise RuntimeError(
                f"{errors} LLM call errors this run vs only {len(scored)} scored "
                f"candidates — treating the run as failed. Check API key / model / rate limits."
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
