"""
vertical_sources.py (Updated)
==============================

Defines the 10 final verticals and maps each to keyword sets,
RSS feeds, and Claude research prompts.

Used by vertical_pipeline.py and vertical_crustdata_refresh.py.
"""

# 10 FINAL VERTICALS
VERTICALS = [
    {
        "id": 0,
        "name": "Energy, Climate & Sustainability Tech",
        "keywords": ["climate", "clean energy", "renewable", "carbon", "emissions", "EV", "grid", "battery", "energy efficiency", "green", "sustainability"],
        "rss_feeds": [
            "https://www.canarymedia.com/feed",
            "https://www.greenbiz.com/feed",
            "https://energypost.eu/feed/",
        ],
    },
    {
        "id": 1,
        "name": "Data Privacy, Governance & Compliance",
        "keywords": ["privacy", "GDPR", "data protection", "PII", "compliance", "DPA", "consent", "data governance", "security"],
        "rss_feeds": [
            "https://www.iapp.org/feed/",
            "https://techcrunch.com/category/privacy/feed/",
        ],
    },
    {
        "id": 2,
        "name": "Fintech, Payments & Financial Compliance",
        "keywords": ["fintech", "AML", "KYC", "compliance", "payments", "banking", "financial crime", "sanctions", "fraud", "lending"],
        "rss_feeds": [
            "https://fintechbusinessweekly.substack.com/feed",
            "https://www.pymnts.com/feed/",
        ],
    },
    {
        "id": 3,
        "name": "Space, Ocean Tech & Advanced Navigation",
        "keywords": ["space", "satellite", "ocean", "maritime", "navigation", "geospatial", "remote sensing", "autonomous vessels"],
        "rss_feeds": [
            "https://spacenews.com/feed/",
            "https://www.marinelink.com/news/rss",
        ],
    },
    {
        "id": 4,
        "name": "AI Governance, Safety & Responsible AI",
        "keywords": ["AI governance", "model risk", "AI safety", "responsible AI", "bias", "LLM", "AI compliance", "model monitoring"],
        "rss_feeds": [
            "https://www.theinformation.com/feed",
            "https://thealgorithmicbridge.substack.com/feed",
        ],
    },
    {
        "id": 5,
        "name": "Biotech, Medtech & Life Sciences Compliance",
        "keywords": ["biotech", "medtech", "pharma", "clinical trials", "HIPAA", "FDA", "drug development", "regulatory", "life sciences"],
        "rss_feeds": [
            "https://endpts.com/feed",
            "https://www.fiercebiotech.com/rss/xml",
            "https://www.biopharmadive.com/feeds/news/",
        ],
    },
    {
        "id": 6,
        "name": "Supply Chain, Logistics & Legal Tech",
        "keywords": ["supply chain", "logistics", "SBOM", "vendor management", "procurement", "traceability", "legal tech", "contract"],
        "rss_feeds": [
            "https://www.lawnext.com/feed",
            "https://www.supplychainbrain.com/feeds/rss.aspx",
        ],
    },
    {
        "id": 7,
        "name": "Cybersecurity, Infrastructure & Operations",
        "keywords": ["cybersecurity", "threat detection", "incident response", "CISO", "security operations", "vulnerability", "zero trust"],
        "rss_feeds": [
            "https://www.darkreading.com/rss.xml",
            "https://blog.cloudflare.com/rss/",
        ],
    },
    {
        "id": 8,
        "name": "Insurance, Risk Management & Real Estate Tech",
        "keywords": ["insurance", "insurtech", "risk management", "underwriting", "claims", "real estate", "construction", "project"],
        "rss_feeds": [
            "https://www.insurancejournal.com/rss/",
            "https://www.constructionexec.com/feed",
        ],
    },
    {
        "id": 9,
        "name": "Healthcare, Interoperability & Agtech",
        "keywords": ["healthcare", "patient data", "interoperability", "EHR", "clinical workflow", "agriculture", "food", "traceability"],
        "rss_feeds": [
            "https://www.mobihealthnews.com/feed",
            "https://www.agritechtoday.com/feed/",
        ],
    },
]


def get_vertical(vertical_id: int) -> dict:
    """Get a vertical by ID."""
    if 0 <= vertical_id < len(VERTICALS):
        return VERTICALS[vertical_id]
    return None


def get_vertical_by_day_of_year(day: int = None) -> dict:
    """Get a vertical by day of year (for rotation)."""
    from datetime import datetime
    if day is None:
        day = datetime.now().timetuple().tm_yday
    vertical_id = day % len(VERTICALS)
    return VERTICALS[vertical_id]


if __name__ == "__main__":
    print("=" * 80)
    print("FINAL 10 VERTICALS for Second Layer VC Pipeline")
    print("=" * 80)
    print()
    for v in VERTICALS:
        print(f"V{v['id']} — {v['name']}")
        print(f"  Keywords: {', '.join(v['keywords'][:6])}...")
        print(f"  RSS Feeds: {len(v['rss_feeds'])} feeds")
        print()
