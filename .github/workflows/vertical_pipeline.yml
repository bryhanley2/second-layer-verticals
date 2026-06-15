"""
Vertical Sources Configuration (V0–V19)
=======================================
Second Layer vertical schema. Changes from prior version:
  - Old V6 (Supply Chain, Logistics & Legal Tech) SPLIT into V6 + V7
  - Old V9 (Healthcare, Interoperability & Agtech) SPLIT into V10 + V11
  - V12–V15: AI Second Layer verticals (opportunity + risk tracks)
  - V16–V19: NET NEW Second Layer verticals

Each vertical: keywords (YC/SEC/TechCrunch filtering), rss_feeds (sector
publications), search_terms (Claude research queries).
"""

VERTICALS = [
    {
        "id": 0,
        "name": "Energy, Climate & Sustainability Tech",
        "keywords": ["climate", "clean energy", "renewable", "carbon", "emissions", "ev", "grid", "battery", "energy", "solar", "sustainability", "decarbon"],
        "rss_feeds": ["https://www.canarymedia.com/feed", "https://www.greenbiz.com/feed", "https://energypost.eu/feed/"],
        "search_terms": [
            "climate tech startup seed round funding 2026",
            "grid software energy seed funding announced",
            "carbon management startup seed round",
        ],
    },
    {
        "id": 1,
        "name": "Data Privacy, Governance & Compliance",
        "keywords": ["privacy", "gdpr", "data protection", "pii", "compliance", "consent", "data governance"],
        "rss_feeds": ["https://iapp.org/feed/", "https://techcrunch.com/category/privacy/feed/"],
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
        "rss_feeds": ["https://fintechbusinessweekly.substack.com/feed", "https://www.pymnts.com/feed/"],
        "search_terms": [
            "fintech compliance seed round funding",
            "AML KYC startup seed funding announced",
            "payments fraud startup seed round",
        ],
    },
    {
        "id": 3,
        "name": "Space, Ocean Tech & Advanced Navigation",
        "keywords": ["space", "satellite", "ocean", "maritime", "navigation", "geospatial", "remote sensing", "autonomous", "aerospace", "debris"],
        "rss_feeds": ["https://spacenews.com/feed/", "https://www.marinelink.com/news/rss"],
        "search_terms": [
            "space tech startup seed round funding",
            "maritime ocean tech seed funding announced",
            "satellite servicing debris startup seed round",
        ],
    },
    {
        "id": 4,
        "name": "AI Governance, Safety & Responsible AI",
        "keywords": ["ai governance", "model risk", "ai safety", "responsible ai", "bias", "llm", "ai compliance", "model monitoring", "evaluation", "observability"],
        "rss_feeds": ["https://venturebeat.com/category/ai/feed/", "https://thealgorithmicbridge.substack.com/feed"],
        "search_terms": [
            "AI governance startup seed funding 2026",
            "LLM evaluation observability seed round",
            "AI safety model monitoring seed funding",
        ],
    },
    {
        "id": 5,
        "name": "Biotech, Medtech & Life Sciences Compliance",
        "keywords": ["biotech", "medtech", "pharma", "clinical trials", "hipaa", "fda", "drug development", "regulatory", "life sciences", "diagnostics"],
        "rss_feeds": ["https://endpts.com/feed", "https://www.fiercebiotech.com/rss/xml", "https://www.biopharmadive.com/feeds/news/"],
        "search_terms": [
            "medtech software startup seed funding 2026",
            "clinical trials technology seed round announced",
            "life sciences compliance startup seed funding",
        ],
    },
    {
        # SPLIT from old V6 — now standalone
        "id": 6,
        "name": "Supply Chain & Logistics",
        "keywords": ["supply chain", "logistics", "freight", "procurement", "traceability", "vendor", "sbom", "shipping", "warehouse", "inventory"],
        "rss_feeds": ["https://www.supplychainbrain.com/feeds/rss.aspx", "https://www.freightwaves.com/news/feed"],
        "search_terms": [
            "supply chain visibility startup seed funding",
            "logistics freight software seed round announced",
            "procurement traceability startup seed funding",
        ],
    },
    {
        # SPLIT from old V6 — now standalone
        "id": 7,
        "name": "Legal Tech & Contract Intelligence",
        "keywords": ["legal tech", "contract", "litigation", "compliance", "paralegal", "law firm", "e-discovery", "legal ai", "legal research"],
        "rss_feeds": ["https://www.lawnext.com/feed", "https://abovethelaw.com/feed/"],
        "search_terms": [
            "legal tech contract AI startup seed funding",
            "litigation e-discovery automation seed round",
            "law firm workflow software seed funding",
        ],
    },
    {
        # Was V7 in old schema
        "id": 8,
        "name": "Cybersecurity, Infrastructure & Operations",
        "keywords": ["cybersecurity", "security", "threat detection", "incident response", "ciso", "vulnerability", "zero trust", "soc", "devsecops"],
        "rss_feeds": ["https://www.darkreading.com/rss.xml", "https://blog.cloudflare.com/rss/"],
        "search_terms": [
            "cybersecurity startup seed round funding 2026",
            "threat detection SOC startup seed funding",
            "cloud security startup seed round announced",
        ],
    },
    {
        # Was V8 in old schema
        "id": 9,
        "name": "Insurance, Risk Management & Real Estate Tech",
        "keywords": ["insurance", "insurtech", "risk management", "underwriting", "claims", "real estate", "construction", "proptech", "permitting"],
        "rss_feeds": ["https://www.insurancejournal.com/rss/", "https://www.constructionexec.com/feed"],
        "search_terms": [
            "insurtech startup seed round funding 2026",
            "AI underwriting claims automation seed funding",
            "real estate construction tech seed round announced",
        ],
    },
    {
        # SPLIT from old V9 — now standalone
        "id": 10,
        "name": "Healthcare & Interoperability",
        "keywords": ["healthcare", "patient", "interoperability", "ehr", "clinical workflow", "care navigation", "prior authorization", "medicare", "telehealth"],
        "rss_feeds": ["https://www.mobihealthnews.com/feed", "https://www.fiercehealthcare.com/rss/xml"],
        "search_terms": [
            "healthcare interoperability startup seed funding",
            "care navigation EHR startup seed round announced",
            "prior authorization automation startup seed funding",
        ],
    },
    {
        # SPLIT from old V9 — now standalone
        "id": 11,
        "name": "Agtech & Food Systems",
        "keywords": ["agriculture", "agtech", "farm", "food", "crop", "livestock", "food traceability", "precision agriculture", "food safety", "supply"],
        "rss_feeds": ["https://www.agfundernews.com/feed", "https://www.agritechtoday.com/feed/"],
        "search_terms": [
            "agtech precision agriculture startup seed funding",
            "food traceability safety startup seed round",
            "farm management software seed funding announced",
        ],
    },
    {
        "id": 12,
        "name": "AI Security, Red-Teaming & Content Authenticity",
        "keywords": ["ai security", "red team", "deepfake", "content authenticity", "provenance", "model security", "jailbreak", "prompt injection", "synthetic media", "watermarking"],
        "rss_feeds": ["https://www.darkreading.com/rss.xml", "https://venturebeat.com/category/security/feed/"],
        "search_terms": [
            "AI security red teaming startup seed funding",
            "deepfake detection content provenance seed round",
            "LLM security prompt injection startup seed funding",
        ],
    },
    {
        "id": 13,
        "name": "AI Agent Infrastructure & Tooling",
        "keywords": ["ai agent", "agentic", "tool calling", "agent authentication", "agent payments", "orchestration", "mcp", "agent infrastructure", "llm tooling"],
        "rss_feeds": ["https://venturebeat.com/category/ai/feed/", "https://techcrunch.com/category/artificial-intelligence/feed/"],
        "search_terms": [
            "AI agent infrastructure startup seed funding 2026",
            "agent authentication payments orchestration seed round",
            "agentic workflow tooling startup seed funding",
        ],
    },
    {
        "id": 14,
        "name": "AI Compute, Energy & Data Center Infrastructure",
        "keywords": ["data center", "cooling", "compute", "gpu", "inference optimization", "energy efficiency", "grid", "power", "thermal", "interconnection"],
        "rss_feeds": ["https://www.datacenterdynamics.com/en/rss/", "https://www.canarymedia.com/feed"],
        "search_terms": [
            "data center cooling efficiency startup seed funding",
            "GPU inference optimization startup seed round",
            "data center power grid software seed funding",
        ],
    },
    {
        "id": 15,
        "name": "Workforce Transition & AI-Augmented Services",
        "keywords": ["reskilling", "upskilling", "workforce", "ai copilot", "human in the loop", "services automation", "labor", "ai training", "talent transition"],
        "rss_feeds": ["https://techcrunch.com/category/startups/feed/", "https://www.hrdive.com/feeds/news/"],
        "search_terms": [
            "workforce reskilling AI transition startup seed funding",
            "AI copilot professional services startup seed round",
            "human in the loop AI services seed funding",
        ],
    },
    {
        # NET NEW — defense buildout creates compliance/supply-chain second layer
        "id": 16,
        "name": "Defense, Dual-Use & Export Compliance",
        "keywords": ["defense", "dual-use", "itar", "export control", "dod", "military", "national security", "defense supply chain", "cmmc", "fedramp"],
        "rss_feeds": ["https://www.defensenews.com/arc/outboundfeeds/rss/", "https://breakingdefense.com/feed/"],
        "search_terms": [
            "defense tech compliance ITAR startup seed funding",
            "export control software startup seed round",
            "defense supply chain security startup seed funding",
        ],
    },
    {
        # NET NEW — robotics adoption creates integration/safety second layer
        "id": 17,
        "name": "Robotics & Physical Automation Enablement",
        "keywords": ["robotics", "robot", "automation", "fleet management", "robot integration", "humanoid", "warehouse automation", "robot safety", "teleoperation"],
        "rss_feeds": ["https://www.therobotreport.com/feed/", "https://techcrunch.com/category/robotics/feed/"],
        "search_terms": [
            "robotics integration software startup seed funding",
            "robot fleet management orchestration seed round",
            "warehouse automation enablement startup seed funding",
        ],
    },
    {
        # NET NEW — aging demographics create care infrastructure second layer
        "id": 18,
        "name": "Aging Economy & Elder Care Infrastructure",
        "keywords": ["elder care", "aging", "senior", "home care", "caregiver", "medicare advantage", "long-term care", "benefits navigation", "longevity"],
        "rss_feeds": ["https://homehealthcarenews.com/feed/", "https://www.mcknights.com/feed/"],
        "search_terms": [
            "elder care coordination startup seed funding",
            "home care operations software seed round announced",
            "senior benefits navigation startup seed funding",
        ],
    },
    {
        # NET NEW — quantum progress creates cryptographic migration second layer
        "id": 19,
        "name": "Post-Quantum Security & Cryptographic Migration",
        "keywords": ["post-quantum", "quantum", "cryptography", "pqc", "encryption migration", "quantum-safe", "nist", "cryptographic inventory", "harvest now decrypt later"],
        "rss_feeds": ["https://thequantuminsider.com/feed/", "https://www.darkreading.com/rss.xml"],
        "search_terms": [
            "post-quantum cryptography startup seed funding",
            "quantum-safe encryption migration seed round",
            "cryptographic inventory discovery startup seed funding",
        ],
    },
    {
        # V20 — Consumer health/wellness brands (CPG-specific sourcing)
        "id": 20,
        "name": "Consumer Health & Wellness Brands",
        "keywords": ["functional food", "functional beverage", "better for you", "protein snack", "prebiotic", "probiotic", "adaptogen", "clean label", "plant based", "gut health", "wellness", "superfood", "non-alcoholic", "sugar free", "gluten free"],
        "rss_feeds": [
            "https://www.foodnavigator-usa.com/rssfeed",
            "https://www.bevnet.com/news/feed/",
            "https://www.nosh.com/feed/",
            "https://www.beautyindependent.com/feed/",
            "https://www.fooddive.com/feeds/news/",
        ],
        "search_terms": [
            "functional snack brand seed funding raised 2026",
            "better-for-you consumer brand seed round food beverage 2025 2026",
            "clean label wellness brand seed funding raised",
            "non-alcoholic beverage startup seed round raised",
            "protein snack brand bootstrapped raising seed round",
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
    print(f"V0-V{len(VERTICALS)-1} SECOND LAYER VERTICALS")
    print("=" * 80)
    for v in VERTICALS:
        print(f"V{v['id']:>2} — {v['name']}")
