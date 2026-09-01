"""
new_sources.py
==============
Extra early-signal sources for the vertical pipeline, wired into
``vertical_pipeline.py`` STEP 1 behind the ``EXTRA_SOURCES`` env toggle
(default on; set ``EXTRA_SOURCES=0`` to skip).

Provides:
    1. source_yc_launches()   — recent YC "Launch HN" posts via the HN Algolia
                                API, keyword-matched to the vertical
    2. source_producthunt()   — newest Product Hunt launches (Atom feed),
                                keyword-matched to the vertical
    3. VC_NEWSLETTER_FEEDS     — feed list consumed by the pipeline's own
                                ``source_vertical_rss()`` (which has the
                                funding-headline extraction these need)

The two source functions return raw records shaped as:
    {"name": str, "description": str, "url": str, "source": str, "yc_batch": str}
``vertical_pipeline._adapt_extra_record()`` maps that onto the full candidate
shape before gating/scoring.
"""

import re
import time
import feedparser
import requests
from datetime import datetime, timedelta, timezone


# ──────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────

def _matches_vertical(text: str, keywords: list) -> bool:
    """Case-insensitive keyword match against an item's text blob."""
    if not text or not keywords:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _is_recent(entry, days: int = 21) -> bool:
    """Filter feed entries to the last N days. Returns True if no date present."""
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    if not pub:
        return True  # don't drop items just because they lack a date
    entry_dt = datetime(*pub[:6], tzinfo=timezone.utc)
    return entry_dt > datetime.now(timezone.utc) - timedelta(days=days)


def _clean(text: str, max_len: int = 400) -> str:
    """Strip HTML tags and collapse whitespace, then truncate."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


# ──────────────────────────────────────────────────────────────────────
#  1. YC LAUNCHES  ("Launch HN" posts)
# ──────────────────────────────────────────────────────────────────────
# YC Launches has no official RSS. The HN Algolia API indexes the
# "Launch HN:" posts under the `launch_hn` tag — the same data behind
# news.ycombinator.com. (The previous implementation queried a
# non-existent `launch_yc` tag and always returned nothing.)

_LAUNCH_HN_RE = re.compile(
    r"Launch HN:\s*(?P<name>[^(]+?)\s*\(YC\s*(?P<batch>[^)]+)\)\s*[\-‐-―−|:]\s*(?P<desc>.+)",
)


def source_yc_launches(vertical: dict, max_results: int = 25, recent_days: int = 240) -> list:
    """Recent YC Launch HN posts matching this vertical's keywords.

    vertical: dict with 'name' and 'keywords' (list of strings).
    recent_days: only consider launches created within this window.
    """
    keywords = vertical.get("keywords", [])
    if not keywords:
        return []

    api = "https://hn.algolia.com/api/v1/search"
    cutoff = int(time.time()) - recent_days * 86400
    results, seen_ids = [], set()

    for kw in keywords[:5]:  # cap keyword fan-out
        try:
            r = requests.get(
                api,
                params={
                    "query": kw,
                    "tags": "launch_hn",
                    "numericFilters": f"created_at_i>{cutoff}",
                    "hitsPerPage": 20,
                },
                timeout=15,
            )
            r.raise_for_status()
            hits = r.json().get("hits", [])
        except Exception as e:
            print(f"[yc_launches] '{kw}' failed: {e}")
            continue

        for hit in hits:
            hit_id = hit.get("objectID")
            if not hit_id or hit_id in seen_ids:
                continue
            seen_ids.add(hit_id)

            title = hit.get("title", "") or ""
            m = _LAUNCH_HN_RE.match(title)
            if m:
                name = m.group("name").strip()
                batch = m.group("batch").strip().upper().replace(" ", "")
                desc = m.group("desc").strip()
            else:
                # Not a parseable "Launch HN: X (YC B) – ..." title — skip rather
                # than push a headline-shaped "company" into the pipeline.
                continue

            # Algolia's full-text match is fuzzy (typo-tolerant, matches comment
            # bodies) — re-check the vertical keywords against the parsed
            # name + pitch so an off-topic launch doesn't slip through.
            if not _matches_vertical(f"{name} {desc}", keywords):
                continue

            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit_id}"
            results.append({
                "name": name,
                "description": desc,
                "url": url,
                "source": f"YC Launch {batch}" if batch else "YC Launch",
                "yc_batch": batch,
            })
            if len(results) >= max_results:
                return results

    return results


# ──────────────────────────────────────────────────────────────────────
#  2. PRODUCT HUNT
# ──────────────────────────────────────────────────────────────────────
# Official Atom feed: https://www.producthunt.com/feed
# Low-signal firehose (~50 newest products); the vertical keyword filter
# is what makes it usable.

def source_producthunt(vertical: dict, max_results: int = 15, recent_days: int = 21) -> list:
    """Newest Product Hunt launches matching the vertical's keywords."""
    keywords = vertical.get("keywords", [])
    if not keywords:
        return []

    results = []
    try:
        feed = feedparser.parse("https://www.producthunt.com/feed")
        for entry in feed.entries:
            if not _is_recent(entry, days=recent_days):
                continue
            title = (entry.get("title", "") or "").strip()
            summary = _clean(entry.get("summary", ""), 300)
            if not _matches_vertical(f"{title} {summary}", keywords):
                continue

            # PH Atom titles are just the product name; tagline is in summary.
            name = title.split("—", 1)[0].strip() if "—" in title else title
            if not name:
                continue
            results.append({
                "name": name[:80],
                "description": summary or title,
                "url": entry.get("link", ""),
                "source": "Product Hunt",
                "yc_batch": "",
            })
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[producthunt] failed: {e}")

    return results


# ──────────────────────────────────────────────────────────────────────
#  3. VC NEWSLETTER FEEDS
# ──────────────────────────────────────────────────────────────────────
# Consumed by vertical_pipeline.source_vertical_rss(), which already does
# "<Company> raises $<N>" headline extraction + seed-stage + keyword
# filtering. Kept here as a plain config list.

VC_NEWSLETTER_FEEDS = [
    "https://www.strictlyvc.com/feed/",              # StrictlyVC
    "https://a16z.com/feed/",                        # a16z
    "https://newcomer.substack.com/feed",            # Newcomer
    "https://www.thegeneralist.com/feed",            # The Generalist
    "https://every.to/feed",                         # Every
    "https://www.notboring.co/feed",                 # Not Boring
    "https://thediff.co/feed",                       # The Diff
]


if __name__ == "__main__":
    v = {
        "name": "Energy, Climate & Sustainability Tech",
        "keywords": ["climate", "energy", "grid", "battery", "solar", "carbon"],
    }
    print(f"Smoke test against vertical: {v['name']}\n")
    for label, fn in (("YC Launches", source_yc_launches), ("Product Hunt", source_producthunt)):
        try:
            hits = fn(v)
            print(f"OK  {label}: {len(hits)} hits")
            for h in hits[:3]:
                print(f"      - {h['name']}  [{h['source']}]  {h['url']}")
        except Exception as e:
            print(f"ERR {label} crashed: {e}")
