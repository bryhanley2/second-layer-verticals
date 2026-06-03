"""
Vertical Sources Configuration (V0–V9, Crustdata-free)
======================================================
Maps each of the 10 verticals to:
1. keywords      — used to filter the YC company dataset by vertical
2. rss_feeds     — sector-specific publications for funding-announcement parsing
3. search_terms  — targeted queries for Claude web research

Each vertical is indexed 0-9, matching the V0-V9 schema in the README and
the rotation used by vertical_pipeline.py.
"""

VERTICALS = [
    {
        "id": 0,
        "name": "Energy, Climate & Sustainability Tech",
        "keywords": ["climate", "clean energy", "renewable", "carbon", "emissions", "ev", "grid", "battery", "energy", "solar", "sustainability", "decarbon"],
        "rss_feeds": [
            "https://www.canarymedia.com/feed",
            "https://www.greenbiz.com/feed",
            "https://energypost.eu/feed/",
        ],
        "search_terms": [
            "climate tech startup seed round funding 2025",
            "grid software energy seed funding announced",
            "carbon management startup seed round",
        ],
    },
    {
        "id": 1,
        "name": "Data Privacy, Governance & Compliance",
        "keywords": ["privacy", "gdpr", "data protection", "pii", "compliance", "consent", "data governance"],
        "rss_feeds": [
            "https://iapp.org/feed/",
            "https://techcrunch.com/category/privacy/feed/",
        ],
        "search_terms": [
            "data privacy startup seed round funding",
            "data governance compliance seed funding",
            "consent management platform seed round",
        ],
    },
    {
        "id": 2,
        "name": "Fintech, Payments & Financial Compliance",
        "keywords": ["fintech", "aml", "kyc", "compliance", "payments", "banking", "financial crime", "sanctions", "fraud", "lending", "regtech"],
        "rss_feeds": [
            "https://fintechbusinessweekly.substack.com/feed",
            "https://www.pymnts.com/feed/",
        ],
        "search_terms": [
            "fintech compliance seed round funding",
            "AML KYC startup seed funding announced",
            "payments fraud startup seed round",
        ],
    },
    {
        "id": 3,
        "name": "Space, Ocean Tech & Advanced Navigation",
        "keywords": ["space", "satellite", "ocean", "maritime", "navigation", "geospatial", "remote sensing", "autonomous", "aerospace"],
        "rss_feeds": [
            "https://spacenews.com/feed/",
            "https://www.marinelink.com/news/rss",
        ],
        "search_terms": [
            "space tech startup seed round funding",
            "maritime ocean tech seed funding announced",
            "geospatial navigation startup seed round",
        ],
    },
    {
        "id": 4,
        "name": "AI Governance, Safety & Responsible AI",
        "keywords": ["ai governance", "model risk", "ai safety", "responsible ai", "bias", "llm", "ai compliance", "model monitoring", "evaluation", "observability"],
        "rss_feeds": [
            "https://venturebeat.com/category/ai/feed/",
            "https://thealgorithmicbridge.substack.com/feed",
        ],
        "search_terms": [
            "AI governance startup seed funding 2025",
            "LLM evaluation observability seed round",
            "AI safety model monitoring seed funding",
        ],
    },
    {
        "id": 5,
        "name": "Biotech, Medtech & Life Sciences Compliance",
        "keywords": ["biotech", "medtech", "pharma", "clinical trials", "hipaa", "fda", "drug development", "regulatory", "life sciences", "diagnostics"],
        "rss_feeds": [
            "https://endpts.com/feed",
            "https://www.fiercebiotech.com/rss/xml",
            "https://www.biopharmadive.com/feeds/news/",
        ],
        "search_terms": [
            "medtech software startup seed funding 2025",
            "clinical trials technology seed round announced",
            "life sciences compliance startup seed funding",
        ],
    },
    {
        "id": 6,
        "name": "Supply Chain, Logistics & Legal Tech",
        "keywords": ["supply chain", "logistics", "sbom", "vendor", "procurement", "traceability", "legal tech", "contract", "freight"],
        "rss_feeds": [
            "https://www.lawnext.com/feed",
            "https://www.supplychainbrain.com/feeds/rss.aspx",
        ],
        "search_terms": [
            "supply chain software startup seed funding",
            "legal tech contract AI seed round announced",
            "logistics visibility startup seed funding",
        ],
    },
    {
        "id": 7,
        "name": "Cybersecurity, Infrastructure & Operations",
        "keywords": ["cybersecurity", "security", "threat detection", "incident response", "ciso", "vulnerability", "zero trust", "soc", "devsecops"],
        "rss_feeds": [
            "https://www.darkreading.com/rss.xml",
            "https://blog.cloudflare.com/rss/",
        ],
        "search_terms": [
            "cybersecurity startup seed round funding 2025",
            "threat detection SOC startup seed funding",
            "cloud security startup seed round announced",
        ],
    },
    {
        "id": 8,
        "name": "Insurance, Risk Management & Real Estate Tech",
        "keywords": ["insurance", "insurtech", "risk management", "underwriting", "claims", "real estate", "construction", "proptech", "permitting"],
        "rss_feeds": [
            "https://www.insurancejournal.com/rss/",
            "https://www.constructionexec.com/feed",
        ],
        "search_terms": [
            "insurtech startup seed round funding 2025",
            "AI underwriting claims automation seed funding",
            "real estate construction tech seed round announced",
        ],
    },
    {
        "id": 9,
        "name": "Healthcare, Interoperability & Agtech",
        "keywords": ["healthcare", "patient", "interoperability", "ehr", "clinical workflow", "agriculture", "agtech", "food", "traceability", "care navigation"],
        "rss_feeds": [
            "https://www.mobihealthnews.com/feed",
            "https://www.agfundernews.com/feed",
        ],
        "search_terms": [
            "healthcare interoperability startup seed funding",
            "care navigation EHR startup seed round announced",
            "agtech food traceability startup seed funding",
        ],
    },
]


def get_vertical(vertical_id: int) -> dict:
    """Get a vertical by ID."""
    if 0 <= vertical_id < len(VERTICALS):
        return VERTICALS[vertical_id]
    return None


def get_vertical_by_day_of_year(day: int = None):
    """Get (index, vertical) by day of year for rotation."""
    from datetime import datetime
    if day is None:
        day = datetime.now().timetuple().tm_yday
    vertical_id = day % len(VERTICALS)
    return vertical_id, VERTICALS[vertical_id]


if __name__ == "__main__":
    print("=" * 80)
    print("V0-V9 VERTICALS (Crustdata-free)")
    print("=" * 80)
    for v in VERTICALS:
        print(f"\nV{v['id']} — {v['name']}")
        print(f"  Keywords:     {', '.join(v['keywords'][:6])}...")
        print(f"  RSS Feeds:    {len(v['rss_feeds'])}")
        print(f"  Search Terms: {len(v['search_terms'])}")
