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
  7. V21 scrape      — V21 only: HTML scrape_targets + run-over-run diff
                       (set V21_SCRAPE=0 to skip)

All candidates pass through the three hard gates before scoring, then the
Second Layer thesis filter, then 9-factor scoring. Writes to the
"Vertical Pipeline" tab with the vertical name annotated.

Usage:
  VERTICAL_INDEX=0 python vertical_pipeline.py   # Energy
  VERTICAL_INDEX=10 python vertical_pipeline.py  # Healthcare
  VERTICAL_INDEX=20 python vertical_pipeline.py  # Consumer Health Brands
  (no override) → rotates by day of year

Required env vars:
  ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
import requests
import feedparser
from pipeline_utils import (
    get_sheet_client, get_anthropic_client, SHEET_ID, MODEL,
    passes_all_gates, evaluate_second_layer_fit, score_candidate,
    verify_size_post_enrichment,
    decision_from_score, write_scored_candidates, read_existing_names,
    send_email_digest, MIN_SCORE_PCT, safe_float, ensure_tab,
    record_llm_error, llm_error_count, llm_error_summary,
)
from vertical_sources import (
    get_vertical, get_vertical_by_day_of_year,
    get_scrape_targets, passes_scrape_filter,
)
from new_sources import source_yc_launches, source_producthunt, VC_NEWSLETTER_FEEDS

VERTICAL_TAB = "Vertical Pipeline"

# Extra early-signal sources (YC Launches, Product Hunt, VC newsletters) run in
# STEP 1 unless EXTRA_SOURCES=0.
EXTRA_SOURCES_ENABLED = os.environ.get("EXTRA_SOURCES", "1").strip() != "0"

# V21 proprietary scrape layer (HTML targets + run-over-run diff). Only V21
# defines scrape_targets, so this is a no-op for every other vertical. Set
# V21_SCRAPE=0 to skip it even for V21.
V21_SCRAPE_ENABLED = os.environ.get("V21_SCRAPE", "1").strip() != "0"
SCRAPE_STATE_TAB = "V21 Scrape Seen"
# Cap on how many never-before-seen companies one scrape run pushes into the
# pipeline — protects the first run (empty state) from processing whole portfolios.
try:
    SCRAPE_MAX_NEW = int(os.environ.get("V21_SCRAPE_MAX_NEW") or "50")
except ValueError:
    SCRAPE_MAX_NEW = 50

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
def source_techcrunch(keywords: list, vertical_name: str) -> list:
    """Parse TechCrunch venture/startup feeds for seed rounds matching the vertical."""
    candidates = []
    tc_feeds = [
        "https://techcrunch.com/category/venture/feed/",
        "https://techcrunch.com/category/startups/feed/",
        "https://techcrunch.com/tag/seed-funding/feed/",
    ]
    funding_pattern = re.compile(
        r"([A-Z][A-Za-z0-9.\- ]{2,40})\s+(?:raises?|secures?|closes?|lands?|nabs?|bags?)\s+\$(\d+(?:\.\d+)?)\s*([MK])",
        re.IGNORECASE,
    )
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
                match = funding_pattern.search(title)
                funding_usd = 0
                name = title.split(" raises")[0].split(" secures")[0].split(" closes")[0].strip()[:80]
                if match:
                    name = match.group(1).strip()[:80]
                    amount = float(match.group(2))
                    unit = match.group(3).upper()
                    funding_usd = amount * (1_000_000 if unit == "M" else 1_000)
                    if funding_usd > 15_000_000:
                        continue
                if not name:
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
    funding_pattern = re.compile(
        r"([A-Z][A-Za-z0-9.\- ]{2,40})\s+(?:raises?|secures?|closes?|announces?|bags?)\s+\$(\d+(?:\.\d+)?)\s*([MK])",
        re.IGNORECASE,
    )
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
                match = funding_pattern.search(title)
                if not match:
                    if not any(k in title.lower() for k in ["seed", "pre-seed"]):
                        continue
                    name_fallback = title.split(" raises")[0].split(" secures")[0].split(" closes")[0].strip()[:80]
                    if not name_fallback:
                        continue
                    candidates.append({
                        "name": name_fallback,
                        "website": entry.get("link", ""),
                        "description": summary[:500],
                        "industry": vertical_name,
                        "hq_city": "", "hq_country": "United States",
                        "founded_date": "", "headcount": 0,
                        "total_funding_usd": 0, "last_funding_round": "seed",
                        "last_funding_date": entry.get("published", ""),
                        "linkedin_url": "",
                        "_source": f"RSS ({feed_url.split('/')[2]})",
                    })
                    continue

                name = match.group(1).strip()
                amount = float(match.group(2))
                unit = match.group(3).upper()
                funding_usd = amount * (1_000_000 if unit == "M" else 1_000)
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
    for term in search_terms:
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
# Source 7: V21 proprietary scrape layer
# ============================================================================
# The five/six sources above are press-and-announcement based — every fund
# scraping YC and TechCrunch sees the same companies. The V21 scrape_targets
# (DOE program ecosystems, specialist-fund portfolios, accelerator cohorts,
# RTO/ISO registries) surface companies BEFORE they hit venture press.
#
# Flow: fetch each target's HTML -> reduce to visible text + link list ->
# Claude extracts company names -> passes_scrape_filter() drops hardware ->
# diff against the "V21 Scrape Seen" tab so only NEW names enter the pipeline.
#
# LIMITATION: this is a static fetch (requests). Fully JS-rendered portfolio
# SPAs return an empty shell and yield nothing until a headless fetch is added;
# such targets are logged as "likely JS-rendered".

_SCRAPE_UA = "Mozilla/5.0 (compatible; SecondLayerVC-research/1.0; +https://bryanhanleyvc.substack.com)"
# Drop non-content blocks (incl. their contents) before extracting text.
# Deliberately conservative — stripping <nav>/<header>/<footer> ate real content
# on sites that nest their listings inside those tags. The extraction prompt is
# told to skip nav/generic text instead.
_TAG_RE = re.compile(r"(?is)<(script|style|noscript|svg|template)\b.*?</\1>")
_ANCHOR_RE = re.compile(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
_STRIP_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _fetch_page_text(url: str, timeout: int = 20) -> str:
    """Fetch a page and reduce it to visible text plus an anchor-text/href list
    (portfolio pages are mostly links). Returns "" on any fetch error."""
    try:
        resp = requests.get(url, headers={"User-Agent": _SCRAPE_UA}, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [scrape] fetch failed: {url} — {e}")
        return ""
    html = _TAG_RE.sub(" ", resp.text)

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


def _looks_js_rendered(page_text: str) -> bool:
    """Static fetch of a JS SPA yields an almost-empty shell."""
    return len(page_text.strip()) < 250


def _extract_companies_from_page(ai_client, url: str, page_text: str, vertical: dict) -> list:
    """Ask Claude to pull operating-company names out of one scraped page.
    Returns list of {name, website, note}. [] on error or empty page."""
    if len(page_text.strip()) < 250:
        return []
    prompt = f"""Text scraped from: {url}

This page is expected to list startups / companies — a VC portfolio, an
accelerator cohort, a government program's awardee or teaming list, or a
market-participant registry.

Extract every entry that is an operating company/startup in or adjacent to:
"{vertical['name']}" — asset-light SOFTWARE for the energy, grid, and
data-center-power buildout.

STRICT RULES:
- Real company names only. Skip nav items, section headers, people's names,
  fund/investor names, report titles, and generic phrases ("Our Portfolio",
  "Learn more", "Read the case study").
- Use ONLY names present in the text below. Do not infer or invent companies.
- If the page lists no companies, return nothing at all.

Return ONE JSON object per line and nothing else:
{{"name": "...", "website": "https://... or empty", "note": "<=12 words on what they do, or empty"}}

--- PAGE TEXT ---
{page_text}"""
    try:
        resp = ai_client.messages.create(
            model=MODEL, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
    except Exception as e:
        record_llm_error(f"V21 scrape extraction {url}", e)
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
        if nm:
            out.append({
                "name": nm[:80],
                "website": str(c.get("website", "") or "").strip()[:300],
                "note": str(c.get("note", "") or "").strip()[:200],
            })
    return out


def source_vertical_scrape(ai_client, sheet_client, vertical: dict) -> list:
    """V21 proprietary scrape layer. Returns candidate-shaped dicts for
    companies found on scrape_targets that were NOT seen in a prior run.
    No-op (returns []) for any vertical without scrape_targets."""
    targets = get_scrape_targets(vertical)
    if not targets:
        return []

    print(f"[V21 scrape] {len(targets)} targets")
    seen = read_existing_names(sheet_client, SCRAPE_STATE_TAB)  # lowercased set
    first_run = not seen
    if first_run:
        print("[V21 scrape] no prior state — first run will record targets without flooding "
              f"the pipeline (cap {SCRAPE_MAX_NEW})")

    new_hits = {}  # name_lower -> (name, website, note, source_url)
    for url in targets:
        page_text = _fetch_page_text(url)
        if not page_text:
            continue
        if _looks_js_rendered(page_text):
            print(f"  [scrape] likely JS-rendered, skipping: {url}")
            continue
        for c in _extract_companies_from_page(ai_client, url, page_text, vertical):
            key = c["name"].lower()
            if key in seen or key in new_hits:
                continue
            ok, reason = passes_scrape_filter(f"{c['name']} {c['note']}", vertical)
            if not ok:
                print(f"  [scrape] filtered {c['name']}: {reason}")
                continue
            new_hits[key] = (c["name"], c["website"], c["note"], url)

    print(f"[V21 scrape] {len(new_hits)} new companies after dedup + hardware filter")

    selected = list(new_hits.values())[:SCRAPE_MAX_NEW]
    if len(new_hits) > SCRAPE_MAX_NEW:
        print(f"[V21 scrape] capping at {SCRAPE_MAX_NEW}; remaining will surface next run")

    # Record every selected name as seen BEFORE gating/scoring, so a company that
    # fails downstream isn't re-extracted every run. The seen tab is cheap to prune.
    _record_scrape_seen(sheet_client, [(n, u, note) for (n, _w, note, u) in selected])

    return [
        _adapt_extra_record(
            {"name": n, "url": w or u, "description": note, "source": "V21 Scrape"},
            vertical["name"],
        )
        for (n, w, note, u) in selected
    ]


def _record_scrape_seen(sheet_client, rows: list) -> None:
    """Append (name, source_url, note) rows to the V21 Scrape Seen tab."""
    if not rows:
        return
    try:
        tab = ensure_tab(
            sheet_client, SCRAPE_STATE_TAB,
            headers=["Company", "First Seen", "Source URL", "Note"], cols=4,
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tab.append_rows([[n, now, u, note] for (n, u, note) in rows])
        print(f"[V21 scrape] recorded {len(rows)} names to '{SCRAPE_STATE_TAB}'")
    except Exception as e:
        print(f"[V21 scrape] could not update '{SCRAPE_STATE_TAB}': {e}")


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


def verify_zero_funding(ai_client, candidates: list) -> None:
    """
    Two-pass funding verification:
      1. For each candidate showing $0, try Crunchbase API (if key configured).
      2. For remaining unverified candidates, ask Claude — but Claude must cite
         a source or return "unverified". No estimation, no extrapolation.

    Populates: total_funding_usd, last_funding_round (the round name like "Series A"),
    last_round_type (explicit round label for the new sheet column),
    last_funding_date, founded_year, _funding_confidence, _funding_source.
    """
    zero = [c for c in candidates if safe_float(c.get("total_funding_usd", 0)) == 0]
    if not zero:
        return

    # ----- Pass 1: Crunchbase lookup -----
    crunchbase_hits = 0
    still_unknown = []
    for c in zero:
        cb_data = _crunchbase_lookup(c["name"])
        if cb_data and cb_data.get("total_funding_usd"):
            c["total_funding_usd"] = cb_data["total_funding_usd"]
            c["last_funding_round"] = cb_data.get("last_funding_type") or c.get("last_funding_round", "")
            c["last_round_type"] = cb_data.get("last_funding_type") or ""
            c["last_funding_date"] = cb_data.get("last_funding_date") or c.get("last_funding_date", "")
            c["founded_year"] = cb_data.get("founded_year") or c.get("founded_year", "")
            c["_funding_confidence"] = "high"
            c["_funding_source"] = "Crunchbase"
            c["_funding_unverified"] = False  # cleared: now verified against Crunchbase
            crunchbase_hits += 1
        else:
            still_unknown.append(c)
    if crunchbase_hits:
        print(f"[Funding verify] Crunchbase: {crunchbase_hits} candidates verified")

    if not still_unknown:
        return

    # ----- Pass 2: Claude verification with strict source-citation rule -----
    names = [c["name"] for c in still_unknown][:40]
    prompt = f"""You are verifying funding and team data for the seed-stage startups below.
DO NOT estimate. DO NOT extrapolate from similar companies. DO NOT use general knowledge.
DO NOT fabricate founder names — this is a CRITICAL anti-hallucination rule.
Only return data you can cite a specific source for.

EXAMPLES OF PROHIBITED FABRICATION:
- Inventing plausible-sounding co-founder names (e.g. "Eric Ness" when the actual co-founder is "Eric Ryan")
- Inventing founder backgrounds (e.g. "ex-AWS/Capgemini" when actually ex-Google/Microsoft)
- Completing the pattern of a founder bio when source data is thin
- Pattern-matching common Silicon Valley names ("Smith, Chen, Patel, etc.")

If you do not know a founder's name or background from a specific source you can cite,
return null. NEVER guess. NEVER fabricate.

For each company, return JSON with these fields:
- total_funding_usd: integer dollar amount, ONLY if you can cite a specific source. Otherwise null.
- last_round_type: the EXACT round name as reported (Pre-seed / Seed / Seed Extension / Series A / Series B / Grant / etc.). Otherwise null.
- last_funding_date: YYYY-MM-DD format if known, otherwise null.
- founded_year: YYYY if known from a specific source, otherwise null.
- founders: array of objects [{{"name": "Full Name", "role": "CEO/CTO/etc.", "background_source": "URL or citation"}}] — ONLY include founders you can verify by name and role from a specific source. If any founder name is uncertain, OMIT THEM ENTIRELY rather than guessing. Empty array if no founders can be verified.
- source_citation: URL or specific reference (e.g. "TechCrunch Jun 2024 announcement", "SEC Form D filed 2024-03-15", "Crunchbase profile").
- confidence: "high" (multiple primary sources agree), "medium" (single primary source like a press release or SEC filing), "low" (general knowledge only, NO specific source), or "unverified" (cannot find).

CRITICAL: If confidence would be "low" or "unverified", set total_funding_usd to null AND founders to [].
Better to return null and empty than to estimate or fabricate.

Companies: {json.dumps(names)}

Return ONLY a JSON object mapping company name to the fields above. No preamble."""
    try:
        resp = ai_client.messages.create(
            model=MODEL, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        verified = json.loads(resp.content[0].text.strip())
        updated = 0
        unverified_count = 0
        for c in still_unknown:
            info = verified.get(c["name"], {})
            if not info:
                continue
            confidence = (info.get("confidence") or "").lower()
            if confidence in ("low", "unverified"):
                c["_funding_confidence"] = confidence
                c["_funding_source"] = info.get("source_citation") or "no source"
                unverified_count += 1
                continue
            if info.get("total_funding_usd") is not None:
                c["total_funding_usd"] = info["total_funding_usd"]
                c["_funding_unverified"] = False  # cleared: cited source provided
                updated += 1
            if info.get("last_round_type"):
                c["last_funding_round"] = info["last_round_type"]
                c["last_round_type"] = info["last_round_type"]
            if info.get("last_funding_date"):
                c["last_funding_date"] = info["last_funding_date"]
            if info.get("founded_year"):
                c["founded_year"] = info["founded_year"]
            # Founders: overwrite ONLY if Claude returned verified founders with citations.
            # If founders array is empty or missing, leave existing data alone (don't blank it out).
            founders_list = info.get("founders") or []
            if founders_list and isinstance(founders_list, list):
                # Format as readable string for sheet column; preserve source citations
                founder_str = "; ".join(
                    f"{f.get('name', '?')} ({f.get('role', 'co-founder')})"
                    for f in founders_list if f.get("name")
                )
                if founder_str:
                    c["founders"] = founder_str
                    c["_founders_verified"] = True
                    c["_founders_sources"] = [f.get("background_source", "") for f in founders_list]
            c["_funding_confidence"] = confidence or "medium"
            c["_funding_source"] = info.get("source_citation") or "Claude verified"
        print(f"[Funding verify] Claude: {updated} verified, {unverified_count} flagged as unverified")
    except Exception as e:
        record_llm_error("funding verification pass", e)
        print("[Funding verify] proceeding with pre-verification data for this batch")


# ============================================================================
# Dedup
# ============================================================================
def deduplicate(candidates: list, existing_names: set) -> list:
    seen = set(existing_names)
    unique = []
    for c in candidates:
        name = str(c.get("name", "")).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
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


def main():
    override = os.environ.get("VERTICAL_INDEX", "")
    if override.strip():
        try:
            idx = int(override)
        except ValueError:
            raise RuntimeError(f"Invalid VERTICAL_INDEX: {override}")
        vertical = get_vertical(idx)
    else:
        idx, vertical = get_vertical_by_day_of_year()

    name = vertical["name"]
    keywords = vertical.get("keywords", [])
    rss_feeds = vertical.get("rss_feeds", [])
    search_terms = vertical.get("search_terms", [])

    print(f"\n{'='*60}")
    print(f"Vertical Pipeline — V{idx}: {name}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    sheet_client = get_sheet_client()
    ai_client = get_anthropic_client()

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
    if V21_SCRAPE_ENABLED:
        candidates.extend(source_vertical_scrape(ai_client, sheet_client, vertical))
    elif get_scrape_targets(vertical):
        print("[V21 scrape] skipped (V21_SCRAPE=0)")
    print(f"\nTotal raw: {len(candidates)}")

    # Step 1b: Verify funding for $0 candidates before gating
    print("\nSTEP 1b: Verifying zero-funding candidates")
    print("-" * 60)
    verify_zero_funding(ai_client, candidates)

    # Step 2: Dedup
    existing = read_existing_names(sheet_client, VERTICAL_TAB)
    candidates = deduplicate(candidates, existing)
    print(f"After dedup: {len(candidates)}")

    # Step 3: Three hard gates
    print(f"\nSTEP 2: Three hard gates")
    print("-" * 60)
    passed = [c for c in candidates if passes_all_gates(c)[0]]
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

    # Step 5: 9-factor scoring
    print(f"\nSTEP 4: 9-factor scoring")
    print("-" * 60)
    scored = []
    for c in passed_sl:
        result = score_candidate(ai_client, c, c["_sl_reason"])
        # MIN_SCORE_PCT may be a single number OR a dict of {stage: threshold}.
        # Look up the threshold based on the candidate's stage in the dict case.
        if isinstance(MIN_SCORE_PCT, dict):
            stage = str(c.get("last_funding_round", "") or "unknown").lower().strip()
            threshold = MIN_SCORE_PCT.get(stage, MIN_SCORE_PCT.get("unknown", 60))
        else:
            threshold = MIN_SCORE_PCT
        if result["weighted_pct"] < threshold:
            continue
        scored.append({
            "candidate": c,
            "sl_reason": c["_sl_reason"],
            **result,
            "decision": decision_from_score(result["weighted_pct"]),
        })
        print(f"  {c['name']:35s} {result['weighted_pct']:5.1f}% [{c.get('_source', '?')}]")

    scored.sort(key=lambda x: x["weighted_pct"], reverse=True)
    print(f"\nScored above threshold: {len(scored)}")

    # Step 6: Write
    print(f"\nSTEP 5: Writing to '{VERTICAL_TAB}' tab")
    print("-" * 60)
    write_scored_candidates(sheet_client, VERTICAL_TAB, scored, vertical_label=name)

    # Step 7: Email
    if scored:
        body_lines = [f"{c['candidate']['name']} — {c['weighted_pct']}% — {c['decision']}"
                      for c in scored[:10]]
        send_email_digest(
            subject=f"Vertical Pipeline {name} — {len(scored)} candidates",
            body=f"Vertical: {name}\n\n" + "\n".join(body_lines),
        )

    print(f"\n{'='*60}")
    print(f"Vertical pipeline V{idx} complete.")
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
