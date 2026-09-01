"""
contact_enrich.py
=================
Best-effort outreach contact lookup for the top-scoring candidates, using ONLY
the company's own website. No paid APIs, no LinkedIn scraping.

enrich_contact(candidate) -> dict:
    {
      "website":  cleaned company URL (or ""),
      "email":    best public email found on the site (or ""),
      "email_source": which page the email came from (or ""),
      "linkedin": company/founder LinkedIn URL if already known or linked from
                  the site (never searched for),
      "note":     short human-readable status
    }

Realistic hit rate for email is ~40-60% — many startups only expose a form.
"""

import re
import time
from urllib.parse import urlparse, urljoin

import requests

_UA = {"User-Agent": "Mozilla/5.0 (compatible; SecondLayerVC-research/1.0)"}

# Pages likely to carry a contact address, in priority order.
_CONTACT_PATHS = ["", "/contact", "/contact-us", "/about", "/team", "/company"]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_MAILTO_RE = re.compile(r'mailto:([^"\'?>\s]+)', re.I)
_LINKEDIN_RE = re.compile(r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in|school)/[A-Za-z0-9\-_%./]+', re.I)

# Local-parts we prefer (higher = better) when several emails are on the page.
_LOCALPART_RANK = {
    "founders": 9, "founder": 9, "team": 7, "hello": 6, "hi": 6,
    "contact": 5, "info": 4, "press": 3, "sales": 2, "support": 1,
}
# Junk / third-party addresses to ignore outright.
_EMAIL_BLOCKLIST = re.compile(
    r"(example\.|sentry\.|wixpress\.|squarespace\.|godaddy\.|\.png|\.jpg|\.svg|"
    r"@sentry|@wix|@shopify|@cloudflare|@google|@facebook|@doubleclick)", re.I,
)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _looks_like_real_site(url: str) -> bool:
    """Reject links that are a news article / discussion, not a company site."""
    d = _domain(url)
    if not d:
        return False
    bad = (
        "news.ycombinator.com", "techcrunch.com", "producthunt.com",
        "crunchbase.com", "linkedin.com", "twitter.com", "x.com",
        "medium.com", "substack.com", "sec.gov", "prnewswire.com",
        "businesswire.com", "globenewswire.com",
    )
    return not any(d == b or d.endswith("." + b) for b in bad)


def _score_email(addr: str, site_domain: str) -> int:
    local, _, dom = addr.lower().partition("@")
    score = _LOCALPART_RANK.get(local, 0)
    if site_domain and (dom == site_domain or dom.endswith("." + site_domain)):
        score += 5  # on-domain address beats a gmail/outlook one
    return score


def _fetch(url: str, timeout: int) -> str:
    try:
        r = requests.get(url, headers=_UA, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and "text/html" in r.headers.get("content-type", "text/html"):
            return r.text
    except Exception:
        pass
    return ""


def enrich_contact(candidate: dict, timeout: int = 12, max_pages: int = 4) -> dict:
    website = str(candidate.get("website", "") or "").strip()
    known_linkedin = str(candidate.get("linkedin_url", "") or "").strip()

    result = {"website": "", "email": "", "email_source": "",
              "linkedin": known_linkedin, "note": ""}

    if not website or not website.startswith("http"):
        result["note"] = "no usable website on candidate"
        return result
    if not _looks_like_real_site(website):
        result["website"] = website
        result["note"] = "website is a news/discussion link, not a company site"
        return result

    result["website"] = website
    site_domain = _domain(website)
    found_emails: dict[str, tuple[int, str]] = {}  # addr -> (score, source_url)
    pages_fetched = 0

    for path in _CONTACT_PATHS:
        if pages_fetched >= max_pages:
            break
        page_url = urljoin(website, path) if path else website
        html = _fetch(page_url, timeout)
        if not html:
            continue
        pages_fetched += 1

        candidates_here = set(_MAILTO_RE.findall(html)) | set(_EMAIL_RE.findall(html))
        for addr in candidates_here:
            addr = addr.strip().strip(".").lower()
            if "@" not in addr or _EMAIL_BLOCKLIST.search(addr):
                continue
            sc = _score_email(addr, site_domain)
            if addr not in found_emails or sc > found_emails[addr][0]:
                found_emails[addr] = (sc, page_url)

        if not result["linkedin"]:
            m = _LINKEDIN_RE.search(html)
            if m:
                result["linkedin"] = m.group(0)

        # Stop early once we have a good on-domain address from the homepage/contact page.
        if found_emails and max(v[0] for v in found_emails.values()) >= 9:
            break
        time.sleep(0.3)

    if found_emails:
        best_addr, (best_score, best_src) = max(found_emails.items(), key=lambda kv: kv[1][0])
        local = best_addr.split("@", 1)[0]
        result["email"] = best_addr
        result["email_source"] = best_src
        if local in _LOCALPART_RANK:
            result["note"] = "role-based email found on site"
        elif best_score >= 5:
            result["note"] = "individual email found on site — verify it's the right contact"
        else:
            result["note"] = "off-domain email found on site — verify before using"
    else:
        result["note"] = f"no public email on {pages_fetched} page(s) checked — use the site's contact form"

    return result
