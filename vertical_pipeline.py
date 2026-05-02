"""
Second Layer Vertical Pipeline
===============================
Runs on-demand for a specific vertical (0-9). Combines:
  1. Vertical-specific Crustdata cache (per-vertical)
  2. Vertical-specific RSS feeds (SpaceNews for space, Fierce Healthcare for health, etc.)
  3. Vertical-targeted Claude research prompts

All candidates pass through the three hard gates before scoring.
Writes to the "Vertical Pipeline" tab with the vertical name annotated.

Usage:
  VERTICAL_INDEX=0 python vertical_pipeline.py   # Space & Defence
  VERTICAL_INDEX=3 python vertical_pipeline.py   # Healthcare
  (no override) → rotates by day of year

Required env vars:
  ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import feedparser
from pipeline_utils import (
    get_sheet_client, get_anthropic_client, SHEET_ID,
    passes_all_gates, evaluate_second_layer_fit, score_candidate,
    decision_from_score, write_scored_candidates, read_existing_names,
    send_email_digest, MIN_SCORE_PCT, safe_float,
)
from vertical_sources import get_vertical, get_vertical_by_day_of_year

import gspread

VERTICAL_TAB = "Vertical Pipeline"


# ============================================================================
# Source 1: Vertical Crustdata Cache
# ============================================================================
def source_vertical_crustdata(client, vertical_idx: int) -> list:
    cache_tab = f"Crustdata Cache - V{vertical_idx}"
    try:
        sheet = client.open_by_key(SHEET_ID)
        tab = sheet.worksheet(cache_tab)
        rows = tab.get_all_records()
        for r in rows:
            r["_source"] = f"Crustdata V{vertical_idx}"
        print(f"[Crustdata V{vertical_idx}] {len(rows)} candidates")
        return rows
    except gspread.WorksheetNotFound:
        print(f"[Crustdata V{vertical_idx}] Tab not found — run vertical_crustdata_refresh.py first")
        return []
    except Exception as e:
        print(f"[Crustdata V{vertical_idx}] Error: {e}")
        return []


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
                    # Still capture for research even without a dollar match
                    # if the title contains "seed" or "pre-seed"
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
                        "hq_city": "",
                        "hq_country": "United States",
                        "founded_date": "",
                        "headcount": 0,
                        "total_funding_usd": 0,
                        "last_funding_round": "seed",
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
                    "hq_city": "",
                    "hq_country": "United States",
                    "founded_date": "",
                    "headcount": 0,
                    "total_funding_usd": funding_usd,
                    "last_funding_round": "seed",
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
    """Use Claude to surface seed-stage companies matching vertical-specific queries."""
    candidates = []
    for term in search_terms:
        prompt = f"""List up to 5 real, specific seed-stage companies matching: "{term}"

Must be:
- Raised <= $15M total
- Founded 2022 or later
- US-based or US-operating
- Real company with named founder and website

Format each as JSON on a single line:
{{"name": "...", "description": "...", "website": "...", "industry": "{vertical_name}", "founded_date": "YYYY", "total_funding_usd": NUMBER, "last_funding_round": "seed"}}

Do NOT include placeholder or made-up companies. If uncertain, skip.
Return ONLY JSON lines, nothing else."""
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
                    c["_source"] = "Claude Vertical Research"
                    candidates.append(c)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"[Claude V-Research '{term}'] Error: {e}")
    print(f"[Claude Vertical Research] {len(candidates)} candidates")
    return candidates


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
def main():
    # Determine which vertical
    override = os.environ.get("VERTICAL_INDEX", "")
    if override.strip():
        try:
            idx = int(override)
        except ValueError:
            raise RuntimeError(f"Invalid VERTICAL_INDEX: {override}")
        vertical = get_vertical(idx)
    else:
        day_of_year = datetime.now().timetuple().tm_yday
        vertical = get_vertical_by_day_of_year(day_of_year)
        idx = vertical['id']

    name = vertical["name"]
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
    candidates.extend(source_vertical_crustdata(sheet_client, idx))
    candidates.extend(source_vertical_rss(rss_feeds, name))
    candidates.extend(source_vertical_claude_research(ai_client, search_terms, name))
    print(f"\nTotal raw: {len(candidates)}")

    # Step 2: Dedup
    existing = read_existing_names(sheet_client, VERTICAL_TAB)
    candidates = deduplicate(candidates, existing)
    print(f"After dedup: {len(candidates)}")

    # Step 3: Three hard gates
    print(f"\nSTEP 2: Three hard gates")
    print("-" * 60)
    passed = []
    for c in candidates:
        ok, _ = passes_all_gates(c)
        if ok:
            passed.append(c)
    print(f"Passed gates: {len(passed)} / {len(candidates)}")

    # Step 4: Second Layer thesis filter
    print(f"\nSTEP 3: Second Layer filter")
    print("-" * 60)
    passed_sl = []
    for c in passed:
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
        if result["weighted_pct"] < MIN_SCORE_PCT:
            continue
        scored.append({
            "candidate": c,
            "sl_reason": c["_sl_reason"],
            **result,
            "decision": decision_from_score(result["weighted_pct"]),
        })
        print(f"  {c['name']:35s} {result['weighted_pct']:5.1f}% [{c.get('_source', '?')}]")

    scored.sort(key=lambda x: x["weighted_pct"], reverse=True)
    print(f"\nScored above {MIN_SCORE_PCT}% threshold: {len(scored)}")

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


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
