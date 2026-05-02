"""
new_sources.py
==============
Drop-in additions for vertical_pipeline.py.

Adds four early-signal sources, each as its own toggleable function:
    1. source_yc_launches()       — YC company launches (web scrape, no official RSS)
    2. source_producthunt()       — ProductHunt newest products (RSS)
    3. source_vertical_rss()      — Expanded vertical-specific RSS feeds
    4. source_vc_newsletters()    — Top VC newsletters (StrictlyVC, TLDR, a16z, etc.)

USAGE in vertical_pipeline.py:
    from new_sources import (
        source_yc_launches,
        source_producthunt,
        source_vertical_rss,
        source_vc_newsletters,
    )

    # In your run() or main() — after existing source calls:
    candidates += source_yc_launches(vertical)
    candidates += source_producthunt(vertical)
    candidates += source_vertical_rss(vertical)
    candidates += source_vc_newsletters(vertical)

Each function returns a list of dicts shaped like the existing pipeline:
    {"name": str, "description": str, "url": str, "source": str}
"""

import re
import feedparser
import requests
from datetime import datetime, timedelta


# ──────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────

def _matches_vertical(text: str, keywords: list) -> bool:
    """Case-insensitive keyword match against an item's text blob."""
    if not text or not keywords:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _is_recent(entry, days: int = 14) -> bool:
    """Filter feed entries to last N days. Returns True if no date present."""
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    if not pub:
        return True  # don't drop items just because they lack a date
    entry_dt = datetime(*pub[:6])
    return entry_dt > datetime.utcnow() - timedelta(days=days)


def _clean(text: str, max_len: int = 400) -> str:
    """Strip HTML tags and truncate."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


# ──────────────────────────────────────────────────────────────────────
#  1. YC LAUNCHES
# ──────────────────────────────────────────────────────────────────────
# YC Launches has no official RSS. We use the YC Algolia API which
# indexes Launch posts under the "launches" tag. This is the same API
# powering ycombinator.com/launches.

def source_yc_launches(vertical: dict, max_results: int = 25) -> list:
    """
    Pull recent YC company launches matching this vertical's keywords.

    vertical: dict with keys 'name' and 'keywords' (list of strings)
    """
    keywords = vertical.get("keywords", [])
    if not keywords:
        return []

    results = []
    api = "https://hn.algolia.com/api/v1/search_by_date"

    # Search YC Launch posts (tagged "launch_yc") for each keyword
    seen_ids = set()
    for kw in keywords[:4]:  # cap keyword fanout
        try:
            r = requests.get(
                api,
                params={
                    "query": kw,
                    "tags": "launch_yc",
                    "hitsPerPage": 15,
                },
                timeout=10,
            )
            r.raise_for_status()
            for hit in r.json().get("hits", []):
                hit_id = hit.get("objectID")
                if hit_id in seen_ids:
                    continue
                seen_ids.add(hit_id)

                title = hit.get("title", "")
                # YC launch titles look like "Launch HN: AcmeCo (YC W26) - One-line pitch"
                m = re.match(
                    r"Launch HN:\s*([^(]+?)\s*\(YC\s*[^)]+\)\s*[-–—]\s*(.+)",
                    title,
                )
                if m:
                    name = m.group(1).strip()
                    desc = m.group(2).strip()
                else:
                    name = title.replace("Launch HN:", "").strip()[:80]
                    desc = title

                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit_id}"

                results.append({
                    "name": name,
                    "description": desc,
                    "url": url,
                    "source": "YC Launches",
                })
                if len(results) >= max_results:
                    return results
        except Exception as e:
            print(f"[yc_launches] '{kw}' failed: {e}")
            continue

    return results


# ──────────────────────────────────────────────────────────────────────
#  2. PRODUCTHUNT
# ──────────────────────────────────────────────────────────────────────
# Official PH feed: https://www.producthunt.com/feed
# Filters incoming products against vertical keywords.

def source_producthunt(vertical: dict, max_results: int = 15) -> list:
    """Pull newest ProductHunt launches matching vertical keywords."""
    keywords = vertical.get("keywords", [])
    if not keywords:
        return []

    feed_url = "https://www.producthunt.com/feed"
    results = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if not _is_recent(entry, days=21):
                continue
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            blob = f"{title} {summary}"

            if not _matches_vertical(blob, keywords):
                continue

            # PH titles are "ProductName — tagline"
            if "—" in title:
                name, tagline = title.split("—", 1)
                name, tagline = name.strip(), tagline.strip()
            else:
                name, tagline = title.strip(), _clean(summary, 200)

            results.append({
                "name": name,
                "description": tagline or _clean(summary, 200),
                "url": entry.get("link", ""),
                "source": "ProductHunt",
            })
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[producthunt] failed: {e}")

    return results


# ──────────────────────────────────────────────────────────────────────
#  3. VERTICAL-SPECIFIC RSS
# ──────────────────────────────────────────────────────────────────────
# Maps each of your 10 verticals to high-quality, vertical-native feeds.
# Update VERTICAL_FEEDS as your verticals evolve.

VERTICAL_FEEDS = {
    # Healthcare / life sciences
    "Healthcare": [
        "https://endpts.com/feed",                      # Endpoints News
        "https://www.fiercebiotech.com/rss/xml",        # Fierce Biotech
        "https://www.biopharmadive.com/feeds/news/",    # BioPharma Dive
        "https://www.mobihealthnews.com/feed",          # MobiHealthNews
    ],
    # Climate / energy
    "Climate": [
        "https://climatetechvc.substack.com/feed",      # CTVC
        "https://newsletter.mcj.vc/feed",               # MCJ
        "https://www.canarymedia.com/feed",             # Canary Media
    ],
    # Fintech / financial crime
    "Fintech": [
        "https://fintechbusinessweekly.substack.com/feed",   # Jason Mikula
        "https://thefintechblueprint.substack.com/feed",     # Lex Sokolin
        "https://www.fintechfutures.com/feed/",
    ],
    # Defense / dual-use / space
    "Defense": [
        "https://spacenews.com/feed/",
        "https://breakingdefense.com/feed/",
    ],
    # AI / ML
    "AI": [
        "https://www.theinformation.com/feed",          # paywall but headlines work
        "https://thealgorithmicbridge.substack.com/feed",
    ],
    # Legal tech / RegTech
    "LegalTech": [
        "https://www.lawnext.com/feed",
        "https://abovethelaw.com/feed/",
    ],
    # Generic catch-all (used if vertical name doesn't match any of the above)
    "_default": [
        "https://techcrunch.com/category/startups/feed/",
        "https://www.eu-startups.com/feed/",
    ],
}


def source_vertical_rss(vertical: dict, max_results: int = 20) -> list:
    """
    Pull recent items from vertical-specific RSS feeds, then filter
    for funding/launch keywords AND vertical keywords.
    """
    name = vertical.get("name", "")
    keywords = vertical.get("keywords", [])

    # Match this vertical to a feed bucket — substring match on vertical name
    feeds = None
    for bucket_name, bucket_feeds in VERTICAL_FEEDS.items():
        if bucket_name == "_default":
            continue
        if bucket_name.lower() in name.lower() or name.lower() in bucket_name.lower():
            feeds = bucket_feeds
            break
    if feeds is None:
        feeds = VERTICAL_FEEDS["_default"]

    funding_signals = [
        "raised", "raises", "seed round", "series a", "pre-seed",
        "funding", "launches", "emerges from stealth", "announces",
    ]

    results = []
    seen_titles = set()

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                if not _is_recent(entry, days=21):
                    continue
                title = entry.get("title", "")
                if title in seen_titles:
                    continue
                summary = _clean(entry.get("summary", ""), 500)
                blob = f"{title} {summary}".lower()

                # Must look like a funding/launch story
                if not any(sig in blob for sig in funding_signals):
                    continue
                # And must match this vertical
                if keywords and not _matches_vertical(blob, keywords):
                    continue

                seen_titles.add(title)
                results.append({
                    "name": title[:120],
                    "description": summary,
                    "url": entry.get("link", ""),
                    "source": f"RSS:{feed_url.split('//')[1].split('/')[0]}",
                })
                if len(results) >= max_results:
                    return results
        except Exception as e:
            print(f"[vertical_rss] {feed_url} failed: {e}")
            continue

    return results


# ──────────────────────────────────────────────────────────────────────
#  4. VC NEWSLETTERS
# ──────────────────────────────────────────────────────────────────────
# Top VC newsletters that consistently surface seed/Series A deals.
# Filtered for vertical keywords AND funding signals.

VC_NEWSLETTER_FEEDS = [
    "https://www.strictlyvc.com/feed/",                # StrictlyVC
    "https://newsletter.tldr.tech/feed",               # TLDR
    "https://a16z.com/feed/",                          # a16z firm blog
    "https://newcomer.substack.com/feed",              # Newcomer (Eric)
    "https://www.thegeneralist.com/feed",              # The Generalist
    "https://every.to/feed",                           # Every (Dan Shipper et al)
    "https://www.notboring.co/feed",                   # Not Boring (Packy)
    "https://thediff.co/feed",                         # The Diff (Byrne Hobart)
]


def source_vc_newsletters(vertical: dict, max_results: int = 15) -> list:
    """Scan top VC newsletters for posts about companies in this vertical."""
    keywords = vertical.get("keywords", [])
    if not keywords:
        return []

    funding_signals = [
        "raised", "raises", "seed", "series a", "pre-seed",
        "funded", "round", "stealth",
    ]

    results = []
    seen_titles = set()

    for feed_url in VC_NEWSLETTER_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:25]:
                if not _is_recent(entry, days=14):
                    continue
                title = entry.get("title", "")
                if title in seen_titles:
                    continue
                summary = _clean(entry.get("summary", ""), 600)
                blob = f"{title} {summary}".lower()

                # Must mention funding AND match the vertical
                if not any(sig in blob for sig in funding_signals):
                    continue
                if not _matches_vertical(blob, keywords):
                    continue

                seen_titles.add(title)
                results.append({
                    "name": title[:120],
                    "description": summary,
                    "url": entry.get("link", ""),
                    "source": f"Newsletter:{feed_url.split('//')[1].split('/')[0]}",
                })
                if len(results) >= max_results:
                    return results
        except Exception as e:
            print(f"[vc_newsletters] {feed_url} failed: {e}")
            continue

    return results


# ──────────────────────────────────────────────────────────────────────
#  CONVENIENCE — RUN ALL FOUR
# ──────────────────────────────────────────────────────────────────────

def source_all_new(vertical: dict) -> list:
    """Run all four new sources and return a combined deduped list."""
    combined = []
    combined += source_yc_launches(vertical)
    combined += source_producthunt(vertical)
    combined += source_vertical_rss(vertical)
    combined += source_vc_newsletters(vertical)

    # Dedupe by URL
    seen_urls = set()
    deduped = []
    for c in combined:
        url = c.get("url", "").strip().lower()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(c)

    return deduped


if __name__ == "__main__":
    # Quick smoke test
    test_vertical = {
        "name": "Healthcare",
        "keywords": ["healthcare", "biotech", "telehealth", "medical"],
    }
    print(f"Testing all four sources against vertical: {test_vertical['name']}\n")

    for fn_name, fn in [
        ("YC Launches", source_yc_launches),
        ("ProductHunt", source_producthunt),
        ("Vertical RSS", source_vertical_rss),
        ("VC Newsletters", source_vc_newsletters),
    ]:
        try:
            hits = fn(test_vertical)
            print(f"✓ {fn_name}: {len(hits)} hits")
            for h in hits[:2]:
                print(f"    • {h['name']}  [{h['source']}]")
        except Exception as e:
            print(f"✗ {fn_name} crashed: {e}")
