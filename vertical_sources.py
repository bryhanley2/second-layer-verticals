"""
Vertical Sources Configuration (V0–V19)
=======================================
Second Layer vertical schema. Changes from prior version:
  - Old V6 (Supply Chain, Logistics & Legal Tech) SPLIT into V6 + V7
  - Old V9 (Healthcare, Interoperability & Agtech) SPLIT into V10 + V11
  - V12–V15: AI Second Layer verticals (opportunity + risk tracks)
  - V16–V19: NET NEW Second Layer verticals

Each vertical: keywords (YC/SEC/TechCrunch filtering), rss_feeds (sector
publications), search_terms (Claude research queries), scrape_targets
(specialist portfolios/cohorts), optional scrape_filters (reject_keywords).
"""

# ---- Scrape pre-filter reject lists --------------------------------------------
# Applied to every vertical's scrape results — the entry isn't a sourceable
# early-stage startup (an exit, a public company, or not a company at all).
_COMMON_SCRAPE_REJECTS = [
    "acquired by", "acquisition by", "was acquired", "ipo'd", "went public",
    "publicly traded", "(nasdaq:", "(nyse:", "shut down", "ceased operations",
    "wound down", "law firm", "consulting firm", "trade association",
    "portfolio company of", "our fund", "spv",
]
# Reusable per-group lists, attached to specific verticals below.
SCRAPE_REJECTS_HARDWARE = [
    "hardware company", "manufactures", "manufacturing plant", "chip fab",
    "device manufacturer", "builds devices", "materials science", "fabrication",
]
SCRAPE_REJECTS_THERAPEUTICS = [
    "drug discovery", "therapeutics", "clinical-stage", "preclinical",
    "drug candidate", "novel molecule", "gene therapy pipeline",
]
SCRAPE_REJECTS_B2B = [
    "b2b saas", "enterprise software", "developer tool", "devtool",
    "api platform", "infrastructure software", "data pipeline", "mlops",
]

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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.congruentvc.com/portfolio",
            "https://lowercarboncapital.com/companies",
            "https://www.cleanenergyventures.com/portfolio/",
            "https://www.energyimpactpartners.com/portfolio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.qedinvestors.com/companies",
            "https://www.nyca.com/portfolio",
            "https://www.commerce.vc/portfolio",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.spacecapital.com/portfolio",
            "https://seraphim.vc/portfolio",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.indiebio.co/portfolio",
            "https://nucleate.org/",
            "https://petri.bio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.dynamo.vc/portfolio",
            "https://interlacevc.com/portfolio",
            "https://www.4dxventures.com/portfolio",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.1011vc.com/portfolio",
            "https://www.ylventures.com/portfolio/",
            "https://forgepointcap.com/portfolio/",
            "https://www.nightdragon.com/portfolio",
            "https://synventures.com/portfolio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.fifthwall.com/companies",
            "https://metaprop.com/portfolio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://rockhealth.com/portfolio/",
            "https://www.406ventures.com/companies",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://agfunder.com/portfolio/",
            "https://www.s2gventures.com/portfolio",
            "https://www.falllinecapital.com/portfolio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://airstreet.com/portfolio",
            "https://www.basis.vc/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://a16z.com/american-dynamism/",
            "https://8vc.com/companies",
            "https://decisivepoint.com/portfolio/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.eclipse.vc/companies",
            "https://luxcapital.com/companies",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://primetimepartners.com/portfolio/",
            "https://www.ziegler.com/ziegler-link-age-fund/",
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
        "scrape_targets": [
            # specialist-fund portfolios / accelerator cohorts for this vertical;
            # diffed run-over-run so new additions surface before venture press
            "https://www.xrclabs.com/portfolio",
            "https://springdaleventures.com/portfolio/",
        ],
    },
    {
        # V21 — Bryan's core thesis: asset-light software that unlocks, accelerates,
        # and optimizes the energy, grid, and thermal buildout AI relies on.
        # Deliberately covers all 4 subsectors in one vertical:
        #   (1) Siting & permitting intelligence
        #   (2) Interconnection & grid navigation
        #   (3) Financing / transaction infrastructure
        #   (4) Thermal / cooling optimization software
        # Keywords are software-specific and exclude hardware/generation terms
        # (no "solar panel," "battery manufacturing," "hardware") to keep sourcing
        # asset-light per thesis. Pair with a tightened funding gate (<=$10M, seed/pre-seed).
        "id": 21,
        "name": "AI Physical Infrastructure Software (Energy, Grid & Thermal)",
        "keywords": [
            # Subsector 1: siting & permitting
            "siting", "permitting", "site selection", "interconnection software",
            # Subsector 2: interconnection & grid navigation
            "interconnection queue", "grid planning", "transmission", "power flow",
            "grid interconnection", "load growth", "grid modernization",
            "grid software", "utility software", "grid AI", "energy grid",
            # Subsector 3: financing / transaction infrastructure
            "tax credit", "transferability", "energy financing", "project finance software",
            "ppa", "power purchase agreement",
            # Subsector 4: thermal / cooling optimization
            "data center cooling", "thermal management", "cooling optimization",
            "liquid cooling software", "water usage effectiveness", "pue optimization",
            # cross-cutting AI-demand framing (broadened to catch plain-language YC-style
            # descriptions like "AI-powered grid planning for utilities", which won't
            # literally contain narrower technical phrases like "interconnection queue")
            "data center power", "ai data center", "grid software", "energy software",
            "power infrastructure", "energy infrastructure", "grid AI", "energy AI",
            "power grid", "utility AI", "clean energy software",
        ],
        "rss_feeds": [
            # TRUE RSS FEEDS ONLY — safe for a standard feed parser.
            "https://www.canarymedia.com/feed",
            "https://www.latitudemedia.com/news/rss.xml",
            "https://www.utilitydive.com/feeds/news/",
            "https://www.datacenterdynamics.com/en/rss/",
        ],

        # ------------------------------------------------------------------
        # SCRAPE TARGETS — HTML pages, NOT RSS. Do not feed these to the RSS
        # parser; they need a separate scrape pass that looks for newly-listed
        # company names since the last run.
        #
        # WHY THESE EXIST: the rss_feeds above are press-and-announcement based,
        # meaning every VC scraping the same sources sees the same companies.
        # The targets below surface companies BEFORE they appear in venture press —
        # this is the proprietary layer of the pipeline.
        #
        # Proven results from this channel type:
        #   - Glacian Technologies  <- university tech-transfer (Penn State)
        #   - GridBoost, ContractPower  <- DOE AI4IX teaming list
        # ------------------------------------------------------------------
        "scrape_targets": [
            # --- DOE program ecosystems (formation-stage, pre-institutional) ---
            # Awardees/performers are US interconnection SOFTWARE teams with
            # non-dilutive federal validation, usually pre-VC.
            "https://www.energy.gov/gdo/ai-interconnection-ai4ix",
            "https://www.energy.gov/eere/i2x/interconnection-innovation-e-xchange-homepage",
            "https://www.connectwerx.org/portfolio-items/",
            "https://www.connectwerx.org/portfolio-items/ppo-cwx-010-gdo-accelerating-interconnection-through-ai-ai4ax/",
            # DOE SBIR/STTR award database — filter energy topic codes. Awardees are
            # pre-institutional software teams with federal non-dilutive validation.
            "https://www.sbir.gov/awards",
            "https://science.osti.gov/sbir/Awards",

            # --- Specialist fund portfolio monitoring (investor-signal convergence) ---
            # These funds keep appearing across the best comps this thesis has found
            # (Pearl Street, Rhizome, Distill, CapeZero). Diff their portfolio pages
            # month over month; NEW additions are checks written before press coverage.
            "https://www.powerhouse.fund/portfolio",
            "https://www.stepchange.vc/portfolio",
            "https://mcj.vc/portfolio",
            # convective.vc removed Sep 2026 — domain is parked.

            # --- Regional / state program cohorts (NY-local, relationship-buildable) ---
            "https://www.nyserda.ny.gov/All-Programs/Innovation-Programs",
            "https://urbanfuturelab.org/portfolio/",
            "https://www.thecleanfight.com/portfolio",

            # --- Specialist accelerator cohorts ---
            # NOTE: heavy hardware skew (e.g. Third Derivative's 2026 cohort was ~90%
            # hardware/materials). Expect a LOW hit rate — the value is the 2-3 software
            # companies per cohort that clear the asset-light filter, not the full list.
            "https://www.third-derivative.org/blog",
            "https://elementalimpact.com/portfolio/",
            "https://www.greentownlabs.com/members/",

            # --- RTO/ISO market participant registrations (commercialization signal) ---
            # A software company registering as a market participant is going commercial.
            # This is how Rewbi surfaced (ERCOT registration).
            "https://www.ercot.com/services/rq/re",
            "https://www.pjm.com/markets-and-operations/etools/oasis",
        ],

        # ------------------------------------------------------------------
        # SCRAPE FILTER RULES — apply to every company found via scrape_targets
        # before it enters the candidate pool. These channels have LOW precision
        # by design (accelerator cohorts are ~90% hardware), so filtering is what
        # makes the channel valuable rather than noisy.
        # ------------------------------------------------------------------
        "scrape_filters": {
            "require_us": True,          # thesis is US-only
            "require_software": True,    # reject hardware/materials/manufacturing
            "reject_keywords": [         # hard-reject signals in company description
                "manufactur", "hardware", "materials", "cold plate", "immersion",
                "coolant distribution", "heat pump", "sensor", "device", "equipment",
                "fabrication", "chemistry", "membrane", "electrolyzer",
            ],
            "max_total_funding": 10_000_000,
        },

        "search_terms": [
            # Subsector 1
            "energy siting permitting software startup seed round 2026",
            "renewable project siting software seed funding raised",
            # Subsector 2
            "grid interconnection software startup seed funding 2026",
            "transmission grid planning software seed round raised",
            "interconnection queue software seed funding announced",
            # Subsector 3
            "clean energy tax credit marketplace seed funding",
            "energy project finance software startup seed round",
            # Subsector 4
            "data center cooling optimization software seed funding 2026",
            "thermal management software startup seed round raised",
            "data center water cooling software seed funding",
            # cross-cutting
            "AI data center energy software startup seed round 2026",
            # DOE program awardees (formation-stage interconnection software teams)
            "DOE AI4IX awardee interconnection software company selected",
            "i2X iQMS queue management software awardee startup",
            "ConnectWERX interconnection AI performer selected company",
            # specialist climate-deal coverage (surfaced CapeZero, Distill Energy, Piq
            # this run — small seed rounds in-range that generalist sources miss)
            "grid software startup pre-seed OR seed $2 million $3 million 2026 Axios",
            "clean energy financing software seed round under $4 million 2026",
            # university tech-transfer / commercialization (surfaced Glacian)
            "university spinout data center cooling software commercialization 2026",
            "NSF I-Corps energy grid software startup commercialization",
            "tech transfer energy software startup first commercial deal 2026",
            # federal non-dilutive validation (pre-institutional software teams)
            "DOE SBIR Phase II award grid interconnection software company",
            "ARPA-E project team grid software startup commercialization",
            # specialist accelerator cohorts (low precision, high proprietary value)
            "Elemental Impact OR Third Derivative cohort grid software startup 2026",
            "NYSERDA OR Urban Future Lab cohort grid energy software startup",
            # investor-signal convergence (funds that keep appearing in the best comps)
            "Powerhouse Ventures OR Stepchange new portfolio grid energy software seed",
        ],
    },
]

# Attach per-vertical scrape reject lists (kept out of the literal above so the
# group constants can be shared). get_scrape_filters() also adds the common set.
_VERTICAL_SCRAPE_REJECTS = {
    2: SCRAPE_REJECTS_HARDWARE,      # Fintech — software only
    6: SCRAPE_REJECTS_HARDWARE,      # Supply Chain — software only
    8: SCRAPE_REJECTS_HARDWARE,      # Cybersecurity — software only
    13: SCRAPE_REJECTS_HARDWARE,     # AI Agents — software only
    5: SCRAPE_REJECTS_THERAPEUTICS,  # Biotech/Medtech — tooling/compliance, not drug pipelines
    20: SCRAPE_REJECTS_B2B,          # Consumer brands — not B2B software
}
for _v in VERTICALS:
    _extra = _VERTICAL_SCRAPE_REJECTS.get(_v["id"])
    if _extra:
        _sf = _v.setdefault("scrape_filters", {})
        _sf["reject_keywords"] = list(_sf.get("reject_keywords", [])) + _extra


def get_vertical(vertical_id: int) -> dict:
    """Get a vertical by ID."""
    if 0 <= vertical_id < len(VERTICALS):
        return VERTICALS[vertical_id]
    return None


def get_scrape_targets(vertical: dict) -> list:
    """
    Return HTML scrape targets for a vertical (empty list if none defined).

    These are NOT RSS feeds — they are pages that must be scraped for newly-listed
    company names. Keep them separate from rss_feeds so a standard feed parser
    never chokes on HTML.
    """
    return vertical.get("scrape_targets", []) or []


def get_scrape_filters(vertical: dict) -> dict:
    """Filter rules applied to companies found via scrape_targets, BEFORE the
    expensive enrichment/scoring steps. A vertical may set "scrape_filters"
    with a "reject_keywords" list; the common rejects are always added."""
    f = dict(vertical.get("scrape_filters") or {})
    f["reject_keywords"] = list(f.get("reject_keywords", [])) + _COMMON_SCRAPE_REJECTS
    return f


def passes_scrape_filter(company_text: str, vertical: dict) -> tuple:
    """Quick pre-filter for a scraped company (name + one-line blurb).
    Returns (passed: bool, reason: str)."""
    text = (company_text or "").lower()
    for kw in get_scrape_filters(vertical).get("reject_keywords", []):
        if kw.lower() in text:
            return False, f"rejected: matched '{kw}'"
    return True, "passed scrape pre-filter"


def get_vertical_by_day_of_year(day: int = None):
    """Get (index, vertical) by day of year for rotation."""
    from datetime import datetime
    if day is None:
        day = datetime.now().timetuple().tm_yday
    vertical_id = day % len(VERTICALS)
    return vertical_id, VERTICALS[vertical_id]


# ============================================================================
# On-demand vertical synthesis
# ============================================================================
def _validate_feeds(urls: list, timeout: int = 12) -> list:
    """Keep only URLs that fetch (HTTP 200) and parse to at least one feed item."""
    import feedparser
    import requests

    ok = []
    for u in urls:
        try:
            r = requests.get(
                u, timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SecondLayerVC-research/1.0)"},
            )
            if r.status_code == 200 and feedparser.parse(r.content).entries:
                ok.append(u)
            else:
                print(f"  [synth] dropped feed (status {r.status_code} / no entries): {u}")
        except Exception as e:
            print(f"  [synth] dropped feed ({e}): {u}")
    return ok


def synthesize_vertical(ai_client, industry: str, model: str) -> dict:
    """Build a vertical config from a free-text industry string.

    Matches the shape of the VERTICALS entries (minus the V21-only scrape
    fields). Claude proposes the name, Second Layer framing, keywords, Claude-
    research search terms, and candidate RSS feeds; proposed feeds are fetched
    and parsed, and only working ones are kept (Claude is unreliable at feed URLs).

    Raises on an empty query or an unparseable model response — there is no
    vertical to run without this.
    """
    import json

    industry = (industry or "").strip()
    if not industry:
        raise ValueError("synthesize_vertical: empty industry string")

    prompt = f"""Build a seed-stage startup sourcing profile for this industry / theme:

"{industry}"

Return ONE JSON object and nothing else:
{{
  "name": "clean 3-8 word vertical name",
  "second_layer_logic": "one sentence — the dominant trend that CREATES the problem the companies in this space solve",
  "keywords": ["12-18 lowercase terms or short phrases that would appear in a company's description, YC profile, SEC filing text, or a funding headline in this space"],
  "search_terms": ["4-6 web-search-style queries for recent seed rounds in this space, each ending with a recency cue like 2026"],
  "rss_feeds": ["0-5 REAL RSS/Atom feed URLs (https://site/feed/ style) for trade press or newsletters covering this industry — only ones you are confident exist; empty list if unsure"]
}}

Rules:
- keywords: specific enough to filter noise, broad enough to catch plain-language pitches. No bare generic words ("software", "ai", "platform") on their own.
- rss_feeds: never invent URLs. Fewer real feeds beats more guesses."""

    resp = ai_client.messages.create(
        model=model, max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:].strip() if text.lower().startswith("json") else text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"synthesize_vertical: model did not return JSON ({e}): {text[:200]}")

    name = str(data.get("name") or industry).strip()[:80]
    keywords = [str(k).strip().lower() for k in (data.get("keywords") or []) if str(k).strip()][:20]
    search_terms = [str(s).strip() for s in (data.get("search_terms") or []) if str(s).strip()][:8]
    proposed = [str(u).strip() for u in (data.get("rss_feeds") or []) if str(u).strip().lower().startswith("http")]

    if not keywords:
        raise RuntimeError(f"synthesize_vertical: no usable keywords generated for {industry!r}")

    print(f"  [synth] validating {len(proposed)} proposed feed(s)")
    valid_feeds = _validate_feeds(proposed)

    return {
        "id": "custom",
        "name": name,
        "second_layer_logic": str(data.get("second_layer_logic") or "").strip()[:300],
        "keywords": keywords,
        "rss_feeds": valid_feeds,
        "search_terms": search_terms,
        "_synthesized_from": industry,
    }


if __name__ == "__main__":
    print("=" * 80)
    print(f"V0-V{len(VERTICALS)-1} SECOND LAYER VERTICALS")
    print("=" * 80)
    for v in VERTICALS:
        print(f"V{v['id']:>2} — {v['name']}")
