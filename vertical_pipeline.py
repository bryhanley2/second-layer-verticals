"""
Second Layer VC Main Sourcing Pipeline
=======================================
Runs daily. Combines:
  1. Crustdata Cache (primary — structured seed-stage data)
  2. YC Algolia (early-stage YC batches)
  3. Hacker News "Show HN" (last 60 days)
  4. ProductHunt (last 30 days)
  5. BetaList (latest launches)
  6. Claude Research (B2B seed-stage queries)
  7. RSS Feeds (curated funding announcement feeds)
  8. GitHub Search (high-star new repos)

All candidates pass through THREE HARD GATES before scoring:
  Gate 1: Stage = Pre-seed / Seed / Series A
  Gate 2: Total funding <= $15M
  Gate 3: Founded <= 5 years ago, last round <= 24 months

Only candidates passing all gates are scored against the 9-factor rubric.
Candidates scoring >=65% are written to the Pipeline tab.

Dropped from previous version (problematic sources):
  - SEC EDGAR (surfaces public company filings)
  - Crunchbase (paywalled / unreliable)
  - Generic "Claude Consumer Research" (produced late-stage bias)
  - Newsletters catch-all (replaced by targeted RSS feeds)

Required env vars:
  ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID
Optional: GITHUB_TOKEN (for GitHub search), GMAIL_USER, GMAIL_APP_PASSWORD
"""

import os
import json
import sys
import time
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import requests
import feedparser

from pipeline_utils import (
    get_sheet_client, get_anthropic_client, SHEET_ID,
    passes_all_gates, evaluate_second_layer_fit, score_candidate,
    decision_from_score, ensure_tab, read_existing_names,
    write_scored_candidates, send_email_digest, safe_float, MIN_SCORE_PCT,
)

import gspread

PIPELINE_TAB = "Pipeline"
FOUNDER_TAB = "Founder Pipeline"
CACHE_TAB = "Crustdata Cache - Main"


# ============================================================================
# SOURCE 1: Crustdata Cache (primary)
# ============================================================================
def source_crustdata_cache(client) -> list:
    """Read from the Crustdata cache tab — this is the primary source."""
    try:
        sheet = client.open_by_key(SHEET_ID)
        tab = sheet.worksheet(CACHE_TAB)
        rows = tab.get_all_records()
        for r in rows:
            r["_source"] = "Crustdata"
        print(f"[Crustdata Cache] {len(rows)} candidates")
        return rows
    except gspread.WorksheetNotFound:
        print("[Crustdata Cache] Tab not found — run crustdata_refresh.py first")
        return []
    except Exception as e:
        print(f"[Crustdata Cache] Error: {e}")
        return []


# ============================================================================
# SOURCE 2: YC Algolia
# ============================================================================
def source_yc_algolia() -> list:
    """Pull recent YC batches via YC directory."""
    candidates = []
    batches = ["W25", "S25", "W26", "F25"]
    for batch in batches:
        try:
            # Try the Algolia search API directly
            url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
            headers = {
                "x-algolia-agent": "Algolia for JavaScript (4.14.3); Browser (lite)",
                "x-algolia-api-key": "9f3b9a7fd6e66c93f2bec4e42e3eb94d",
                "x-algolia-application-id": "45BWZJ1SGC",
            }
            payload = {
                "requests": [{
                    "indexName": "YCCompany_production",
                    "params": f"query=&facetFilters=%5B%5B%22batch%3A{batch}%22%5D%5D&hitsPerPage=50"
                }]
            }
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            if r.status_code == 200:
                hits = r.json().get("results", [{}])[0].get("hits", [])
                for c in hits:
                    candidates.append({
                        "name": c.get("name", ""),
                        "website": c.get("website", ""),
                        "description": c.get("long_description", c.get("one_liner", "")),
                        "industry": c.get("industry", ""),
                        "hq_city": c.get("city", ""),
                        "hq_country": "United States",
                        "founded_date": str(c.get("year_founded", datetime.now().year)),
                        "headcount": c.get("team_size", 0),
                        "total_funding_usd": 0,
                        "last_funding_round": "seed",
                        "last_funding_date": "",
                        "linkedin_url": c.get("linkedin_url", ""),
                        "_source": f"YC {batch}",
                    })
        except Exception as e:
            print(f"[YC {batch}] Error: {e}")
    print(f"[YC Algolia] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 3: Hacker News "Show HN"
# ============================================================================
def source_hn_show() -> list:
    """Pull recent Show HN posts via Algolia HN API."""
    candidates = []
    try:
        # Show HN posts from last 60 days
        cutoff = int((datetime.now() - timedelta(days=60)).timestamp())
        url = f"https://hn.algolia.com/api/v1/search?tags=show_hn&numericFilters=created_at_i>{cutoff}&hitsPerPage=100"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            for h in hits:
                title = h.get("title", "") or ""
                # Try to extract company/product name from "Show HN: X – Y" pattern
                name = ""
                if ":" in title:
                    after = title.split(":", 1)[1].strip()
                    name = after.split("–")[0].split("-")[0].split(",")[0].strip()
                if not name:
                    continue
                candidates.append({
                    "name": name[:80],
                    "website": h.get("url", ""),
                    "description": title,
                    "industry": "",
                    "hq_city": "",
                    "hq_country": "United States",
                    "founded_date": str(datetime.now().year),
                    "headcount": 0,
                    "total_funding_usd": 0,
                    "last_funding_round": "pre-seed",
                    "last_funding_date": "",
                    "linkedin_url": "",
                    "_source": "HN Show",
                })
    except Exception as e:
        print(f"[HN Show] Error: {e}")
    print(f"[HN Show] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 4: Seed DB / Axios Pro Rata RSS (replaces ProductHunt)
# ============================================================================
def source_axios_prorata() -> list:
    """Pull seed funding news from Axios Pro Rata — covers early-stage rounds."""
    candidates = []
    feeds = [
        "https://www.axios.com/pro/health-tech-deals/rss",
        "https://www.axios.com/pro/fintech-deals/rss",
        "https://www.axios.com/feeds/feed.rss",
    ]
    funding_pattern = re.compile(
        r"([A-Z][A-Za-z0-9.\- ]{2,40})\s+(?:raises?|secures?|closes?|lands?|bags?)\s+\$(\d+(?:\.\d+)?)\s*([MK])",
        re.IGNORECASE,
    )
    seed_keywords = ["seed", "pre-seed", "series a", "early-stage", "early stage"]

    for feed_url in feeds:
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
                    "industry": "",
                    "hq_city": "",
                    "hq_country": "United States",
                    "founded_date": "",
                    "headcount": 0,
                    "total_funding_usd": funding_usd,
                    "last_funding_round": "seed",
                    "last_funding_date": entry.get("published", ""),
                    "linkedin_url": "",
                    "_source": "Axios",
                })
        except Exception as e:
            print(f"[Axios {feed_url}] Error: {e}")
    print(f"[Axios Pro Rata] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 5: BetaList
# ============================================================================
def source_betalist() -> list:
    candidates = []
    try:
        feed = feedparser.parse("https://betalist.com/feed")
        for entry in feed.entries[:40]:
            name = (entry.get("title", "") or "").strip()[:80]
            if not name:
                continue
            candidates.append({
                "name": name,
                "website": entry.get("link", ""),
                "description": entry.get("summary", "")[:500],
                "industry": "",
                "hq_city": "",
                "hq_country": "",
                "founded_date": str(datetime.now().year),
                "headcount": 0,
                "total_funding_usd": 0,
                "last_funding_round": "pre-seed",
                "last_funding_date": "",
                "linkedin_url": "",
                "_source": "BetaList",
            })
    except Exception as e:
        print(f"[BetaList] Error: {e}")
    print(f"[BetaList] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 6: Claude B2B Research (targeted, seed-stage only)
# ============================================================================
def source_claude_research(ai_client) -> list:
    """Use Claude to surface recently-funded seed-stage companies in specific themes."""
    candidates = []
    themes = [
        "seed-stage B2B SaaS companies that raised their seed round in the last 90 days solving compliance or regulatory problems",
        "pre-seed infrastructure startups solving enterprise workflow problems created by AI adoption in the last 60 days",
        "seed-stage healthcare AI companies with US-based founders that raised in the last 90 days",
        "seed-stage fintech compliance or regtech startups that raised in the last 60 days",
        "seed-stage cybersecurity or data privacy startups solving problems created by cloud adoption that raised recently",
    ]
    for theme in themes:
        prompt = f"""List up to 5 real, specific companies that match this description:
{theme}

Only include companies that:
- Raised <= $15M total
- Were founded 2022 or later
- Have a named founder and website

Format each company as JSON on a single line:
{{"name": "...", "description": "...", "website": "...", "industry": "...", "founded_date": "YYYY", "total_funding_usd": NUMBER, "last_funding_round": "seed"}}

Do NOT include placeholder or fictional companies. If you're not sure, skip it.
Return ONLY the JSON lines, nothing else."""
        try:
            response = ai_client.messages.create(
                model="claude-opus-4-7",
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
                    c.setdefault("hq_city", "")
                    c.setdefault("hq_country", "United States")
                    c.setdefault("headcount", 0)
                    c.setdefault("last_funding_date", "")
                    c.setdefault("linkedin_url", "")
                    c["_source"] = "Claude Research"
                    candidates.append(c)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"[Claude Research] Error: {e}")
    print(f"[Claude Research] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 7: Funding RSS Feeds
# ============================================================================
def source_rss_funding() -> list:
    """Parse funding-focused RSS feeds for recent seed rounds."""
    candidates = []
    feeds = [
        "https://techcrunch.com/category/startups/feed/",
        "https://news.crunchbase.com/feed/",
        "https://techcrunch.com/tag/seed-funding/feed/",
        "https://venturebeat.com/category/venture/feed/",
        "https://www.geekwire.com/feed/",
        "https://medcitynews.com/feed/",
        "https://www.fiercehealthcare.com/rss/xml",
    ]
    funding_pattern = re.compile(
        r"([A-Z][A-Za-z0-9.\- ]{2,40})\s+(?:raises?|secures?|closes?|bags?)\s+\$(\d+(?:\.\d+)?)\s*([MK])",
        re.IGNORECASE,
    )
    seed_keywords = ["seed", "pre-seed", "series a"]

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title = (entry.get("title", "") or "").strip()
                summary = (entry.get("summary", "") or "").strip()
                combined = f"{title} {summary}"
                if not any(k in combined.lower() for k in seed_keywords):
                    continue
                match = funding_pattern.search(title)
                if not match:
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
                    "industry": "",
                    "hq_city": "",
                    "hq_country": "United States",
                    "founded_date": "",
                    "headcount": 0,
                    "total_funding_usd": funding_usd,
                    "last_funding_round": "seed",
                    "last_funding_date": entry.get("published", ""),
                    "linkedin_url": "",
                    "_source": "RSS Funding",
                })
        except Exception as e:
            print(f"[RSS {feed_url}] Error: {e}")
    print(f"[RSS Funding] {len(candidates)} candidates")
    return candidates


# ============================================================================
# SOURCE 8: GitHub Search
# ============================================================================
def source_github() -> list:
    """Search GitHub for recently-created repos with 100+ stars (early signal)."""
    candidates = []
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[GitHub] No GITHUB_TOKEN, skipping")
        return candidates

    # Repos created in last 90 days with 100+ stars
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    query = f"stars:>100 created:>{cutoff}"
    url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=stars&per_page=30"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            for repo in r.json().get("items", []):
                owner = repo.get("owner", {}).get("login", "")
                name = repo.get("name", "")
                if not name:
                    continue
                candidates.append({
                    "name": name[:80],
                    "website": repo.get("html_url", ""),
                    "description": (repo.get("description") or "")[:500],
                    "industry": "Developer Tools",
                    "hq_city": "",
                    "hq_country": "United States",
                    "founded_date": (repo.get("created_at", "") or "")[:4],
                    "headcount": 0,
                    "total_funding_usd": 0,
                    "last_funding_round": "pre-seed",
                    "last_funding_date": "",
                    "linkedin_url": "",
                    "_source": "GitHub",
                })
    except Exception as e:
        print(f"[GitHub] Error: {e}")
    print(f"[GitHub] {len(candidates)} candidates")
    return candidates


# ============================================================================
# Deduplication
# ============================================================================
def deduplicate(candidates: list, existing_names: set) -> list:
    """Drop candidates already in Pipeline tab or duplicates within this run."""
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
# Main orchestrator
# ============================================================================
def main():
    print(f"\n{'='*60}")
    print(f"Second Layer Main Pipeline — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    sheet_client = get_sheet_client()
    ai_client = get_anthropic_client()

    # Step 1: Pull from all sources
    print("STEP 1: Pulling candidates from sources")
    print("-" * 60)
    all_candidates = []
    all_candidates.extend(source_crustdata_cache(sheet_client))
    all_candidates.extend(source_yc_algolia())
    all_candidates.extend(source_hn_show())
    all_candidates.extend(source_axios_prorata())
    all_candidates.extend(source_betalist())
    all_candidates.extend(source_claude_research(ai_client))
    all_candidates.extend(source_rss_funding())
    all_candidates.extend(source_github())

    print(f"\nTotal raw candidates: {len(all_candidates)}")

    # Step 1b: Verify funding for Crustdata candidates with missing ($0) funding data.
    # Verify zero-funding candidates across ALL sources (not just Crustdata).
    # Two-pass: Crunchbase API (if CRUNCHBASE_API_KEY set), then Claude with strict
    # source-citation rule. Avoids letting well-funded companies through with $0 labels.
    print("\nSTEP 1b: Verifying zero-funding candidates")
    print("-" * 60)
    zero_funded = [c for c in all_candidates if safe_float(c.get("total_funding_usd", 0)) == 0]
    if zero_funded:
        # Flag SEC Form D candidates with $0 as likely SAFE wrappers (low confidence)
        sec_zero = [c for c in zero_funded if c.get("_source", "").startswith("SEC")]
        for c in sec_zero:
            c["_needs_verification"] = True
            c["_verification_reason"] = "SEC Form D reported $0 — likely SAFE wrapper or restructuring"
        print(f"Found {len(zero_funded)} zero-funding candidates ({len(sec_zero)} from SEC Form D)")
        # Reuse vertical_pipeline's verify_zero_funding (Crunchbase + strict Claude)
        try:
            from vertical_pipeline import verify_zero_funding
            verify_zero_funding(ai_client, zero_funded)
        except ImportError:
            print("[Warning] verify_zero_funding not importable — skipping strict verification")
    else:
        print("No zero-funding candidates — skipping verification")
    existing = read_existing_names(sheet_client, PIPELINE_TAB)
    all_candidates = deduplicate(all_candidates, existing)
    print(f"After dedup against existing pipeline: {len(all_candidates)}")

    # Step 3: Three hard gates
    print(f"\nSTEP 2: Applying three hard gates")
    print("-" * 60)
    passed_gates = []
    gate_fails = {"stage": 0, "funding": 0, "age": 0, "other": 0}
    for c in all_candidates:
        ok, reason = passes_all_gates(c)
        if not ok:
            if "stage" in reason:
                gate_fails["stage"] += 1
            elif "funding" in reason:
                gate_fails["funding"] += 1
            elif "age" in reason or "year" in reason or "month" in reason:
                gate_fails["age"] += 1
            else:
                gate_fails["other"] += 1
            continue
        passed_gates.append(c)
    print(f"Gates passed: {len(passed_gates)} / {len(all_candidates)}")
    print(f"Failures — stage: {gate_fails['stage']}, funding: {gate_fails['funding']}, age: {gate_fails['age']}, other: {gate_fails['other']}")

    # Step 4: Second Layer thesis filter
    print(f"\nSTEP 3: Second Layer thesis filter (threshold >= 2)")
    print("-" * 60)
    passed_sl = []
    for c in passed_gates:
        sl_score, sl_reason = evaluate_second_layer_fit(ai_client, c)
        if sl_score < 2:
            continue
        c["_sl_score"] = sl_score
        c["_sl_reason"] = sl_reason
        passed_sl.append(c)
    print(f"Passed Second Layer filter: {len(passed_sl)} / {len(passed_gates)}")

    # Step 5: 9-factor scoring
    print(f"\nSTEP 4: 9-factor scoring")
    print("-" * 60)
    scored = []
    for c in passed_sl:
        result = score_candidate(ai_client, c, c["_sl_reason"])
        if result["weighted_pct"] < MIN_SCORE_PCT:
            continue
        scored.append({
            "candidate": c,
            "sl_reason": c["_sl_reason"],
            **result,
            "decision": decision_from_score(result["weighted_pct"]),
        })
        print(f"  {c['name']:35s} {result['weighted_pct']:5.1f}% [{c.get('_source', '?')}]")

    # Sort by score
    scored.sort(key=lambda x: x["weighted_pct"], reverse=True)

    print(f"\nScored above {MIN_SCORE_PCT}% threshold: {len(scored)}")

    # Step 6: Write to sheet
    print(f"\nSTEP 5: Writing to Pipeline tab")
    print("-" * 60)
    write_scored_candidates(sheet_client, PIPELINE_TAB, scored)

    # Step 7: Email digest (silent fail)
    if scored:
        body_lines = [f"{c['candidate']['name']} — {c['weighted_pct']}% — {c['decision']}"
                      for c in scored[:10]]
        send_email_digest(
            subject=f"Pipeline Daily Digest — {len(scored)} candidates above {MIN_SCORE_PCT}%",
            body="\n".join(body_lines),
        )

    print(f"\n{'='*60}")
    print("Main pipeline complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
