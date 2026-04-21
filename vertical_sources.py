"""
Vertical Sources Configuration
==============================
Maps each of the 10 verticals to:
1. Crustdata industry keywords (for the API filter)
2. Sector-specific RSS feeds (for funding announcement parsing)
3. Search terms for Claude web research

Each vertical is indexed 0-9 matching the rotation used by the vertical pipeline.
"""

VERTICAL_CONFIG = {
    0: {
        "name": "Space & Defence AI",
        "crustdata_keywords": [
            "aerospace", "space", "satellite", "defense", "defence",
            "earth observation", "space intelligence",
        ],
        "rss_feeds": [
            "https://spacenews.com/feed/",
            "https://www.satellitetoday.com/feed/",
            "https://breakingdefense.com/feed/",
        ],
        "search_terms": [
            "space startup seed round funding",
            "defence tech seed funding announced",
            "satellite data seed round",
        ],
    },
    1: {
        "name": "AI Governance & Model Risk",
        "crustdata_keywords": [
            "artificial intelligence", "machine learning", "MLOps",
            "AI safety", "AI governance", "model monitoring",
        ],
        "rss_feeds": [
            "https://venturebeat.com/category/ai/feed/",
            "https://www.theinformation.com/feed",
        ],
        "search_terms": [
            "AI governance startup seed funding",
            "model monitoring MLOps seed round",
            "AI compliance tool seed funding",
        ],
    },
    2: {
        "name": "Fintech Compliance & AML",
        "crustdata_keywords": [
            "fintech", "regtech", "compliance", "anti-money laundering",
            "KYC", "financial crime",
        ],
        "rss_feeds": [
            "https://www.finextra.com/rss/headlines.aspx",
            "https://fintechbusinessweekly.substack.com/feed",
        ],
        "search_terms": [
            "fintech compliance seed round",
            "AML KYC startup seed funding",
            "regtech seed round announced",
        ],
    },
    3: {
        "name": "Healthcare Navigation & Clinical AI",
        "crustdata_keywords": [
            "healthcare", "health tech", "clinical AI", "medical AI",
            "healthcare navigation", "health insurance",
        ],
        "rss_feeds": [
            "https://www.fiercehealthcare.com/rss/xml",
            "https://www.mobihealthnews.com/feed",
            "https://rockhealth.com/feed/",
        ],
        "search_terms": [
            "healthcare AI seed round funding",
            "clinical AI startup seed funding",
            "health tech seed round announced",
        ],
    },
    4: {
        "name": "Cybersecurity & Cloud Security",
        "crustdata_keywords": [
            "cybersecurity", "cloud security", "information security",
            "endpoint security", "zero trust", "SASE",
        ],
        "rss_feeds": [
            "https://www.darkreading.com/rss.xml",
            "https://cyberscoop.com/feed/",
            "https://www.theregister.com/security/headlines.atom",
        ],
        "search_terms": [
            "cybersecurity startup seed funding",
            "cloud security seed round",
            "zero trust startup seed funding",
        ],
    },
    5: {
        "name": "Legal AI & Contract Risk",
        "crustdata_keywords": [
            "legal tech", "legaltech", "contract AI", "legal AI",
            "contract analysis", "compliance",
        ],
        "rss_feeds": [
            "https://www.artificiallawyer.com/feed/",
            "https://www.law.com/international-edition/feed/",
        ],
        "search_terms": [
            "legal AI seed round",
            "legal tech seed funding",
            "contract intelligence startup seed",
        ],
    },
    6: {
        "name": "Data Privacy & PII",
        "crustdata_keywords": [
            "data privacy", "PII", "privacy tech", "data governance",
            "GDPR", "data protection",
        ],
        "rss_feeds": [
            "https://iapp.org/news/feed/",
        ],
        "search_terms": [
            "data privacy startup seed funding",
            "PII protection seed round",
            "privacy tech seed announced",
        ],
    },
    7: {
        "name": "Supply Chain & SBOM Security",
        "crustdata_keywords": [
            "supply chain security", "SBOM", "software supply chain",
            "open source security", "container security",
        ],
        "rss_feeds": [
            "https://www.darkreading.com/rss.xml",
        ],
        "search_terms": [
            "software supply chain security seed",
            "SBOM startup seed funding",
            "open source security seed round",
        ],
    },
    8: {
        "name": "Consumer Fintech & Personal Finance",
        "crustdata_keywords": [
            "consumer fintech", "personal finance", "neobank",
            "wealth management", "financial planning",
        ],
        "rss_feeds": [
            "https://www.finextra.com/rss/headlines.aspx",
            "https://fintechbusinessweekly.substack.com/feed",
        ],
        "search_terms": [
            "consumer fintech seed funding",
            "personal finance startup seed round",
            "neobank seed funding announced",
        ],
    },
    9: {
        "name": "Climate Tech & Energy Transition",
        "crustdata_keywords": [
            "climate tech", "clean energy", "energy transition",
            "carbon capture", "renewable energy", "sustainability tech",
        ],
        "rss_feeds": [
            "https://www.ctvcnews.com/feed",
            "https://sightlineclimate.com/feed",
        ],
        "search_terms": [
            "climate tech seed round funding",
            "clean energy startup seed funding",
            "carbon capture seed round",
        ],
    },
}


def get_vertical(index: int) -> dict:
    """Get vertical config by index, with safe fallback."""
    if index not in VERTICAL_CONFIG:
        raise ValueError(f"Invalid vertical index: {index}. Must be 0-9.")
    return VERTICAL_CONFIG[index]


def get_vertical_name(index: int) -> str:
    return get_vertical(index).get("name", f"Vertical {index}")


def get_vertical_by_day_of_year(day_of_year: int) -> tuple[int, dict]:
    """Rotate through verticals based on day of year."""
    idx = day_of_year % 10
    return idx, get_vertical(idx)
