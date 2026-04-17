"""
Second Layer VC — Vertical Pipeline
Runs one industry vertical per day on a rotating 10-day cycle.
Each vertical has its own RSS feeds, keywords, and Claude research prompt.
Results log to a dedicated "Vertical Pipeline" tab in Google Sheets
and are emailed as a digest.

Verticals (rotate by day % 10):
  0 — Space & Defence AI
  1 — AI Governance & Model Risk
  2 — Fintech Compliance & AML
  3 — Healthcare Navigation & Clinical AI
  4 — Cybersecurity & Cloud Security
  5 — Legal AI & Contract Risk
  6 — Data Privacy & PII
  7 — Supply Chain & SBOM Security
  8 — Consumer Fintech & Personal Finance
  9 — Climate Tech & Energy Transition
"""

import os, json, re, time, datetime, smtplib
import requests
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic
from sheets_logger import get_previously_seen_companies

# ── ENV ────────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EMAIL_SENDER      = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]
EMAIL_RECIPIENT   = os.environ["EMAIL_RECIPIENT"]
GOOGLE_SHEET_ID   = os.environ.get("GOOGLE_SHEET_ID", "")
MIN_SCORE_PCT     = float(os.environ.get("MIN_SCORE_PCT", "65"))

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; second-layer-vertical-pipeline/1.0)",
    "Accept": "application/json, text/html",
}

# ── VERTICALS CONFIG ───────────────────────────────────────────────────────────
VERTICALS = [
    # 0 — Space & Defence AI
    {
        "name": "Space & Defence AI",
        "dominant_trend": "Commercial satellite proliferation + defence spending surge",
        "second_layer_logic": (
            "SpaceX drove launch costs down 95% → thousands of satellites in orbit → "
            "creates downstream demand for earth observation intelligence, "
            "space cybersecurity, dual-use defence AI, ground segment software, "
            "and space traffic management"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups building in the following "
            "Space & Defence AI Second Layer categories:\n"
            "- Earth observation intelligence and geospatial analytics platforms\n"
            "- Space cybersecurity and satellite attack surface protection\n"
            "- Dual-use defence AI applied to satellite or geospatial data\n"
            "- Ground segment software and constellation operations tooling\n"
            "- Space traffic management and collision avoidance platforms\n"
            "- Synthetic data generation for defence and space AI training\n\n"
            "These should be companies that exist BECAUSE of satellite proliferation "
            "— NOT satellite manufacturers themselves."
        ),
        "keywords": [
            "satellite", "earth observation", "geospatial", "space", "defence",
            "dual-use", "constellation", "orbit", "hyperspectral", "sar imagery",
            "space cybersecurity", "ground segment", "space traffic", "synthetic data",
            "intelligence surveillance", "isr", "vleo", "remote sensing",
        ],
        "rss_feeds": [
            ("https://spacenews.com/feed/", "SpaceNews"),
            ("https://payloadspace.com/feed/", "Payload"),
            ("https://www.satellitetoday.com/feed/", "SatelliteToday"),
        ],
    },

    # 1 — AI Governance & Model Risk
    {
        "name": "AI Governance & Model Risk",
        "dominant_trend": "Enterprise AI adoption at scale",
        "second_layer_logic": (
            "61% of VC went to AI in 2025 → enterprises deploying AI models at scale → "
            "creates governance gap, regulatory liability, bias drift, and compliance risk → "
            "AI governance, model validation, and risk management platforms"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in AI governance and model risk:\n"
            "- AI model validation and testing platforms\n"
            "- Model risk management for financial institutions\n"
            "- AI compliance and audit trail infrastructure\n"
            "- Responsible AI and bias detection tools\n"
            "- AI policy enforcement and guardrails\n"
            "- LLM security and prompt injection protection\n\n"
            "These solve problems CREATED BY AI adoption, not AI companies themselves."
        ),
        "keywords": [
            "ai governance", "model risk", "responsible ai", "ai compliance",
            "model validation", "bias detection", "llm security", "prompt injection",
            "ai audit", "ai guardrails", "mlops governance", "ai policy",
            "model monitoring", "fairness", "explainability", "ai regulation",
        ],
        "rss_feeds": [
            ("https://venturebeat.com/feed/", "VentureBeat"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 2 — Fintech Compliance & AML
    {
        "name": "Fintech Compliance & AML",
        "dominant_trend": "Global fintech expansion and digital payments growth",
        "second_layer_logic": (
            "Fintech expanded access to financial services globally → "
            "regulatory burden grew proportionally → "
            "AML, KYC/KYB, sanctions screening, and financial crime compliance "
            "became mandatory bottlenecks for every fintech company"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in fintech compliance:\n"
            "- AML (anti-money laundering) automation platforms\n"
            "- KYC/KYB identity verification and screening tools\n"
            "- Sanctions screening and watchlist monitoring\n"
            "- Financial crime detection and investigation platforms\n"
            "- Regulatory reporting automation for banks and fintechs\n"
            "- Compliance workflow orchestration for financial services\n\n"
            "These solve problems CREATED BY fintech growth, not fintechs themselves."
        ),
        "keywords": [
            "aml", "kyc", "kyb", "anti-money laundering", "sanctions", "fintech compliance",
            "financial crime", "fraud detection", "regulatory reporting", "compliance automation",
            "identity verification", "transaction monitoring", "regtech",
            "bank compliance", "fincrime", "ofac", "watchlist",
        ],
        "rss_feeds": [
            ("https://www.fintechfutures.com/feed/", "Fintech Futures"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 3 — Healthcare Navigation & Clinical AI
    {
        "name": "Healthcare Navigation & Clinical AI",
        "dominant_trend": "Healthcare digitization and EHR proliferation",
        "second_layer_logic": (
            "Healthcare digitized rapidly → EHR fragmentation and administrative burden grew → "
            "clinical documentation, prior authorization, care navigation, and billing "
            "became unsustainable bottlenecks → AI-native workflow tools fill the gap"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in healthcare navigation and clinical AI:\n"
            "- AI-powered clinical documentation and note summarization\n"
            "- Prior authorization automation platforms\n"
            "- Patient care navigation and benefits decoding tools\n"
            "- Healthcare revenue cycle automation\n"
            "- HIPAA-compliant AI workflow tools for providers\n"
            "- Care coordination and referral management platforms\n\n"
            "These solve problems CREATED BY healthcare digitization, not EHRs themselves."
        ),
        "keywords": [
            "hipaa", "clinical ai", "prior auth", "care navigation", "ehr",
            "revenue cycle", "clinical documentation", "healthcare workflow",
            "patient advocacy", "medical billing", "care coordination",
            "health data", "clinical notes", "prior authorization",
            "medicare", "medicaid", "value-based care",
        ],
        "rss_feeds": [
            ("https://medcitynews.com/feed/", "MedCityNews"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 4 — Cybersecurity & Cloud Security
    {
        "name": "Cybersecurity & Cloud Security",
        "dominant_trend": "Cloud adoption explosion and remote work normalization",
        "second_layer_logic": (
            "Cloud adoption created multi-cloud complexity, fragmented visibility, "
            "and expanding attack surfaces → "
            "CSPM, CIEM, DevSecOps, supply chain security, and identity security "
            "became essential infrastructure categories"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in cybersecurity:\n"
            "- Cloud security posture management (CSPM)\n"
            "- Identity and access management security\n"
            "- Supply chain and software dependency security\n"
            "- API security and protection platforms\n"
            "- DevSecOps and developer security tooling\n"
            "- Threat detection and incident response automation\n\n"
            "These solve problems CREATED BY cloud adoption, not cloud providers themselves."
        ),
        "keywords": [
            "cybersecurity", "cloud security", "cspm", "devsecops", "appsec",
            "supply chain security", "sbom", "identity security", "zero trust",
            "threat detection", "incident response", "vulnerability management",
            "api security", "container security", "soc automation",
        ],
        "rss_feeds": [
            ("https://www.darkreading.com/rss.xml", "Dark Reading"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 5 — Legal AI & Contract Risk
    {
        "name": "Legal AI & Contract Risk",
        "dominant_trend": "Legal AI adoption and enterprise contract complexity",
        "second_layer_logic": (
            "Legal AI made document drafting accessible to non-lawyers → "
            "malpractice and compliance risk grew → "
            "contract intelligence, compliance-grade legal workflows, "
            "and legal operations automation became essential"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in legal AI and contract risk:\n"
            "- Contract intelligence and risk analysis platforms\n"
            "- Legal workflow automation for compliance teams\n"
            "- Contract lifecycle management for enterprises\n"
            "- Regulatory change monitoring and legal research tools\n"
            "- Legal operations and matter management platforms\n"
            "- IP management and trademark monitoring tools\n\n"
            "These solve problems CREATED BY legal AI adoption, not legal AI itself."
        ),
        "keywords": [
            "legaltech", "contract intelligence", "contract risk", "legal ai",
            "legal workflow", "clm", "contract lifecycle", "compliance legal",
            "regulatory monitoring", "legal operations", "matter management",
            "ip management", "trademark", "legal compliance", "eDiscovery",
        ],
        "rss_feeds": [
            ("https://techcrunch.com/feed/", "TechCrunch"),
            ("https://www.law.com/rss/", "Law.com"),
        ],
    },

    # 6 — Data Privacy & PII
    {
        "name": "Data Privacy & PII",
        "dominant_trend": "Data broker proliferation and regulatory expansion",
        "second_layer_logic": (
            "750+ data brokers openly trade personal data → "
            "GDPR, CCPA, and privacy regulations created compliance mandates → "
            "consumer data removal, enterprise privacy engineering, "
            "and consent management became required infrastructure"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in data privacy and PII:\n"
            "- Consumer personal data removal and opt-out automation\n"
            "- Enterprise privacy compliance engineering platforms\n"
            "- Consent management and cookie compliance tools\n"
            "- Data discovery and PII scanning platforms\n"
            "- GDPR/CCPA compliance automation for enterprises\n"
            "- Data loss prevention for SaaS environments\n\n"
            "These solve problems CREATED BY data proliferation, not data platforms themselves."
        ),
        "keywords": [
            "data privacy", "pii", "gdpr", "ccpa", "data broker", "privacy compliance",
            "consent management", "data deletion", "personal data removal",
            "privacy engineering", "data discovery", "dlp", "data protection",
            "privacy automation", "cookie consent", "right to erasure",
        ],
        "rss_feeds": [
            ("https://iapp.org/feed/", "IAPP"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 7 — Supply Chain & SBOM Security
    {
        "name": "Supply Chain & SBOM Security",
        "dominant_trend": "Open source adoption and software supply chain complexity",
        "second_layer_logic": (
            "Open source software became ubiquitous → "
            "Log4Shell, SolarWinds, and npm attacks proved supply chain risk → "
            "SBOM compliance mandates, dependency scanning, "
            "and software supply chain security became regulatory requirements"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in supply chain and SBOM security:\n"
            "- Software bill of materials (SBOM) generation and management\n"
            "- Open source dependency scanning and vulnerability detection\n"
            "- Software supply chain risk management platforms\n"
            "- Package registry security and malicious package detection\n"
            "- Third-party vendor risk management automation\n"
            "- Hardware and firmware supply chain security\n\n"
            "These solve problems CREATED BY open source adoption, not open source itself."
        ),
        "keywords": [
            "sbom", "supply chain security", "dependency scanning", "open source security",
            "vendor risk", "third party risk", "software composition analysis",
            "sca", "package security", "firmware security", "hardware security",
            "supply chain risk", "software supply chain", "dependency management",
        ],
        "rss_feeds": [
            ("https://www.darkreading.com/rss.xml", "Dark Reading"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 8 — Consumer Fintech & Personal Finance
    {
        "name": "Consumer Fintech & Personal Finance",
        "dominant_trend": "Fintech expansion and embedded finance proliferation",
        "second_layer_logic": (
            "Fintech expanded credit, payments, and financial products to millions → "
            "complexity, debt traps, and financial confusion grew proportionally → "
            "personal finance management, debt navigation, "
            "subscription tracking, and financial literacy tools emerged"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage consumer fintech startups:\n"
            "- Personal finance management and budgeting apps\n"
            "- Debt payoff and credit building tools\n"
            "- Subscription and recurring expense management\n"
            "- Financial literacy and money education platforms\n"
            "- Fee transparency and banking comparison tools\n"
            "- Immigrant financial services and cross-border banking\n\n"
            "These solve problems CREATED BY fintech expansion, for everyday consumers."
        ),
        "keywords": [
            "personal finance", "budgeting", "debt payoff", "credit building",
            "subscription management", "financial literacy", "fee transparency",
            "money management", "savings automation", "financial wellness",
            "immigrant banking", "credit score", "overdraft", "banking app",
        ],
        "rss_feeds": [
            ("https://www.fintechfutures.com/feed/", "Fintech Futures"),
            ("https://techcrunch.com/feed/", "TechCrunch"),
        ],
    },

    # 9 — Climate Tech & Energy Transition
    {
        "name": "Climate Tech & Energy Transition",
        "dominant_trend": "Energy transition and ESG regulatory expansion",
        "second_layer_logic": (
            "Energy transition created grid complexity, carbon accounting mandates, "
            "and ESG disclosure requirements → "
            "carbon tracking, grid intelligence, ESG reporting automation, "
            "and clean energy operations software became essential infrastructure"
        ),
        "claude_prompt": (
            "Find 10 real pre-seed or seed-stage startups in climate tech and energy transition:\n"
            "- Carbon accounting and emissions tracking platforms\n"
            "- ESG reporting and disclosure automation\n"
            "- Grid intelligence and energy management software\n"
            "- Clean energy asset monitoring and optimisation\n"
            "- Supply chain carbon footprint measurement\n"
            "- Climate risk modelling and insurance underwriting\n\n"
            "These solve problems CREATED BY the energy transition, for enterprises navigating it."
        ),
        "keywords": [
            "carbon accounting", "esg", "emissions tracking", "climate risk",
            "grid intelligence", "energy management", "clean energy", "net zero",
            "scope 3", "carbon footprint", "esg reporting", "sustainability",
            "renewable energy software", "energy transition", "climate compliance",
        ],
        "rss_feeds": [
            ("https://techcrunch.com/feed/", "TechCrunch"),
            ("https://www.greenbiz.com/rss.xml", "GreenBiz"),
        ],
    },
]

# ── SCORING (reused from main pipeline) ───────────────────────────────────────
SECOND_LAYER_CONTEXT = """
SECOND LAYER APPROACH:
Find startups solving problems CREATED BY dominant industries, not being IN them.
- AI adoption → model governance risk → AI governance platforms
- Satellite proliferation → earth observation intelligence gap → analytics platforms
- Fintech expansion → AML/KYC friction → compliance automation
- Healthcare digitization → HIPAA bottlenecks → HIPAA workflow tools
FAILS if it IS the dominant industry (an LLM itself, a satellite manufacturer).
"""

SCORING_RUBRIC = """
EARLY-STAGE SCORING (Pre-Seed / Seed only). Score 0-10 per factor.
If a factor cannot be assessed due to limited info, score 5 (neutral).
Reserve 8-10 for genuinely exceptional signals only.

1A FMF(14%):  9=prior exit+domain expertise, 7=strong domain bg, 5=adjacent, 3=limited
1B Tech(11%): 9=working product with differentiation, 7=prototype, 5=MVP, 3=concept only
1C Commit(10%):9=quit job+fully committed, 7=fulltime recent, 5=part-time, 3=side project
2A PMF(15%):  9=obsessed early users/waitlist/pilots, 7=positive signals, 5=some interest, 3=unclear
3A TAM(12%):  9=$50B+, 7=$10-50B, 5=$1-10B, 3=$100M-1B, 0=<$100M
3B Timing(11%):9=regulatory/structural catalyst NOW, 7=beatable comp, 5=crowded, 3=poor timing
5 TrxQl(10%): 9=accelerator/named pilots/press, 7=early traction signals, 5=some, 3=none visible
6 CapEff(10%): 9=capital-light model, 7=efficient, 5=avg, 3=capital-intensive
7 Investor(7%):9=top-tier VC/YC, 7=notable angels, 5=unknown angels, 3=no outside capital
"""

WEIGHTS = {
    "1A": 0.14, "1B": 0.11, "1C": 0.10,
    "2A": 0.15, "3A": 0.12, "3B": 0.11,
    "5":  0.10, "6":  0.10, "7":  0.07,
}

SCORE_PROMPT = """You are a VC analyst applying the Second Layer investment framework.

{context}

{rubric}

Research and score this company:
Name: {name}
Description: {description}
Vertical: {vertical}
Source: {source}

CRITICAL: Early-stage evaluation only. Do NOT penalise for lacking revenue or growth metrics.
Score 5 (neutral) for unknown factors, not lower.

Respond ONLY with a single valid JSON object:
{{"company_name":"string","founded":"YYYY or unknown","stage":"Pre-Seed/Seed/unknown","raise":"$XM or unknown","vertical":"concise label","what_they_do":"2-3 sentences","second_layer_alignment":true,"second_layer_logic":"First Layer trend → risk/problem → solution","scores":{{"1A":5,"1B":5,"1C":5,"2A":5,"3A":5,"3B":5,"5":5,"6":5,"7":5}},"weighted_score":5.0,"score_pct":50.0,"decision":"★★ PROBABLY PASS","key_strength":"one sentence","key_weakness":"one sentence","stage_gate":"PASS or FAIL"}}"""


def is_fund(name):
    n = name.lower()
    fund_kw = ["fund", "capital partners", "investment", "holdings", "ventures llc",
               "partners lp", "partners llc", "management llc", "asset management"]
    return any(k in n for k in fund_kw)


def is_late_stage(text):
    t = text.lower()
    late_kw = ["series b", "series c", "series d", "series e", "series a",
               "growth equity", "pre-ipo", "late stage",
               "$50 million", "$75 million", "$100 million",
               "$50m", "$75m", "$100m"]
    return any(k in t for k in late_kw)


# ── SOURCING ───────────────────────────────────────────────────────────────────
def source_rss(vertical_config):
    companies = []
    keywords = vertical_config["keywords"]
    for feed_url, feed_name in vertical_config["rss_feeds"]:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            for item in items[:30]:
                title = item.findtext("title", "")
                desc  = item.findtext("description", "")
                combined = f"{title} {desc}".lower()
                if any(kw in combined for kw in keywords) and not is_late_stage(combined):
                    companies.append({
                        "name": title[:80],
                        "description": desc[:300],
                        "source": feed_name,
                    })
        except Exception as e:
            print(f"RSS {feed_name} error: {e}")
    print(f"RSS: {len(companies)} candidates")
    return companies[:8]


def source_claude_vertical(vertical_config):
    companies = []
    try:
        prompt = f"""You are a VC researcher specializing in seed-stage startups.

Vertical: {vertical_config['name']}
Second Layer logic: {vertical_config['second_layer_logic']}

{vertical_config['claude_prompt']}

Strict requirements:
- Real companies you know about, founded 2019-2025
- ONLY Pre-Seed or Seed stage — no Series A or later
- Lesser-known companies preferred over household names

Respond ONLY with a JSON array:
[
  {{"name": "CompanyName", "description": "What they do and the Second Layer logic in one sentence"}},
  ...
]"""

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        raw  = re.sub(r"^```json\s*|^```\s*|\s*```$", "", resp.content[0].text.strip())
        hits = json.loads(raw)
        for hit in hits:
            name = hit.get("name", "")
            desc = hit.get("description", "")
            if name and not is_fund(name):
                companies.append({
                    "name": name,
                    "description": desc,
                    "source": f"Claude — {vertical_config['name']}",
                })
        print(f"Claude vertical: {len(companies)} candidates")
    except Exception as e:
        print(f"Claude vertical error: {e}")
    return companies[:12]


def source_yc_vertical(vertical_config):
    """Pull YC companies matching vertical keywords."""
    companies = []
    keywords = vertical_config["keywords"]
    try:
        url = "https://algolia.ycombinator.com/v1/search"
        for kw in keywords[:3]:
            params = {"query": kw, "hitsPerPage": 10}
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            for hit in resp.json().get("hits", []):
                name = hit.get("name", "")
                desc = hit.get("long_description", "") or hit.get("short_description", "")
                combined = f"{name} {desc}".lower()
                if not name or is_fund(name) or is_late_stage(combined):
                    continue
                companies.append({
                    "name": name,
                    "description": desc[:300],
                    "source": "YC",
                })
            time.sleep(0.5)
    except Exception as e:
        print(f"YC vertical error: {e}")
    print(f"YC vertical: {len(companies)} candidates")
    return companies[:6]


# ── SCORING ────────────────────────────────────────────────────────────────────
def score_company(co, vertical_name):
    prompt = SCORE_PROMPT.format(
        context=SECOND_LAYER_CONTEXT,
        rubric=SCORING_RUBRIC,
        name=co["name"],
        description=co.get("description", "No description available"),
        vertical=vertical_name,
        source=co.get("source", "Unknown"),
    )
    for attempt in range(2):
        try:
            if attempt > 0:
                time.sleep(30)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", resp.content[0].text.strip())
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                continue
            data = json.loads(m.group())
            scores = data.get("scores", {})
            ws  = sum(scores.get(k, 0) * v for k, v in WEIGHTS.items())
            pct = ws * 10
            data["weighted_score"] = round(ws, 2)
            data["score_pct"]      = round(pct, 1)
            data["source"]         = co.get("source", "")
            data["vertical_focus"] = vertical_name

            stage = data.get("stage", "").lower()
            late  = ["series a", "series b", "series c", "series d", "late stage"]
            if any(s in stage for s in late):
                print(f"  Stage gate FAIL: {co['name']}")
                return None

            if pct >= 85:   data["decision"] = "★★★★★ STRONG YES"
            elif pct >= 75: data["decision"] = "★★★★ YES"
            elif pct >= 65: data["decision"] = "★★★ DEEP DIVE"
            elif pct >= 55: data["decision"] = "★★ PROBABLY PASS"
            else:           data["decision"] = "★ HARD PASS"
            return data
        except Exception as e:
            if "429" in str(e) and attempt == 0:
                time.sleep(30)
            else:
                print(f"  Score error {co['name']}: {e}")
                break
    return None


# ── GOOGLE SHEETS LOGGING ──────────────────────────────────────────────────────
def log_to_sheets(results, vertical_name):
    """Append scored results to Vertical Pipeline tab in Google Sheets."""
    try:
        import google.oauth2.service_account as sa
        import googleapiclient.discovery as gd

        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
        creds_data = json.loads(creds_json)
        creds = sa.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = gd.build("sheets", "v4", credentials=creds, cache_discovery=False)
        sheets  = service.spreadsheets()

        tab_name = "Vertical Pipeline"
        today    = datetime.date.today().strftime("%Y-%m-%d")

        # Ensure tab exists
        meta = sheets.get(spreadsheetId=GOOGLE_SHEET_ID).execute()
        existing = [s["properties"]["title"] for s in meta["sheets"]]
        if tab_name not in existing:
            sheets.batchUpdate(
                spreadsheetId=GOOGLE_SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
            ).execute()
            # Write header
            header = [["Date", "Vertical", "Company", "Stage", "Raise", "Score %",
                        "Decision", "Second Layer Logic", "What They Do",
                        "Key Strength", "Key Weakness", "Source"]]
            sheets.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{tab_name}!A1",
                valueInputOption="RAW",
                body={"values": header}
            ).execute()

        rows = []
        for r in results:
            rows.append([
                today,
                vertical_name,
                r.get("company_name", ""),
                r.get("stage", ""),
                r.get("raise", ""),
                f"{r.get('score_pct', 0):.1f}%",
                r.get("decision", ""),
                r.get("second_layer_logic", ""),
                r.get("what_they_do", ""),
                r.get("key_strength", ""),
                r.get("key_weakness", ""),
                r.get("source", ""),
            ])

        if rows:
            # Find last row
            existing_vals = sheets.values().get(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{tab_name}!A:A"
            ).execute().get("values", [])
            next_row = len(existing_vals) + 1

            sheets.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{tab_name}!A{next_row}",
                valueInputOption="RAW",
                body={"values": rows}
            ).execute()
            print(f"Logged {len(rows)} rows to '{tab_name}' tab")
    except Exception as e:
        print(f"Sheets logging error: {e}")


# ── EMAIL DIGEST ───────────────────────────────────────────────────────────────
def send_email(results, vertical_config):
    if not results:
        print("No results to email")
        return

    today        = datetime.date.today().strftime("%B %d, %Y")
    vertical_name = vertical_config["name"]
    qualified     = [r for r in results if r.get("score_pct", 0) >= MIN_SCORE_PCT]

    subject = f"[Vertical Pipeline] {vertical_name} — {len(qualified)} qualified | {today}"

    # Build HTML
    rows_html = ""
    for r in sorted(results, key=lambda x: x.get("score_pct", 0), reverse=True):
        pct      = r.get("score_pct", 0)
        decision = r.get("decision", "")
        bg       = "#e8f5e9" if pct >= 75 else "#fff8e1" if pct >= 65 else "#fafafa"
        rows_html += f"""
        <tr style="background:{bg}">
          <td style="padding:8px;font-weight:bold">{r.get('company_name','')}</td>
          <td style="padding:8px">{r.get('stage','')}</td>
          <td style="padding:8px;font-weight:bold">{pct:.1f}%</td>
          <td style="padding:8px">{decision}</td>
          <td style="padding:8px;font-size:12px">{r.get('second_layer_logic','')}</td>
          <td style="padding:8px;font-size:12px">{r.get('key_strength','')}</td>
          <td style="padding:8px;font-size:12px;color:#888">{r.get('source','')}</td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:1100px;margin:0 auto">
    <h2 style="color:#1a237e">Second Layer Vertical Pipeline</h2>
    <h3 style="color:#333">{vertical_name}</h3>
    <p style="color:#666">{today} &nbsp;|&nbsp; {len(results)} scored &nbsp;|&nbsp;
       <strong>{len(qualified)} qualified (≥{MIN_SCORE_PCT:.0f}%)</strong></p>

    <div style="background:#f5f5f5;padding:12px;border-radius:6px;margin-bottom:20px">
      <strong>Second Layer Logic:</strong><br>
      <span style="color:#555">{vertical_config['second_layer_logic']}</span>
    </div>

    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#1a237e;color:white">
        <th style="padding:10px;text-align:left">Company</th>
        <th style="padding:10px;text-align:left">Stage</th>
        <th style="padding:10px;text-align:left">Score</th>
        <th style="padding:10px;text-align:left">Decision</th>
        <th style="padding:10px;text-align:left">Second Layer Logic</th>
        <th style="padding:10px;text-align:left">Key Strength</th>
        <th style="padding:10px;text-align:left">Source</th>
      </tr>
      {rows_html}
    </table>

    <p style="color:#999;font-size:11px;margin-top:20px">
      Second Layer VC Pipeline &nbsp;|&nbsp; bryanhanleyvc.com
    </p>
    </body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECIPIENT
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Email error: {e}")


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    # Select today's vertical
    day_of_year = datetime.date.today().timetuple().tm_yday
    vertical_config = VERTICALS[day_of_year % len(VERTICALS)]
    vertical_name   = vertical_config["name"]

    print(f"\n{'='*60}")
    print(f"VERTICAL PIPELINE — {vertical_name}")
    print(f"Date: {datetime.date.today()} | Day {day_of_year} | Index {day_of_year % len(VERTICALS)}")
    print(f"{'='*60}\n")

    # Get previously seen to avoid re-scoring
    try:
        previously_seen = get_previously_seen_companies(GOOGLE_SHEET_ID)
    except Exception:
        previously_seen = set()

    # Source candidates
    print("--- Sourcing ---")
    candidates = []
    candidates.extend(source_claude_vertical(vertical_config)); time.sleep(2)
    candidates.extend(source_rss(vertical_config));             time.sleep(2)
    candidates.extend(source_yc_vertical(vertical_config));     time.sleep(2)

    # Dedup
    seen, unique = set(), []
    for co in candidates:
        key = co["name"].lower().strip()
        if key not in seen and len(key) > 2 and key not in previously_seen:
            seen.add(key)
            unique.append(co)

    print(f"\nCandidates: {len(candidates)} raw → {len(unique)} unique & fresh")

    # Score top candidates (cap at 15 to manage API costs)
    print(f"\n--- Scoring (up to 15) ---")
    results = []
    for co in unique[:15]:
        if is_late_stage(f"{co.get('name','')} {co.get('description','')}"):
            continue
        print(f"Scoring: {co['name']}")
        scored = score_company(co, vertical_name)
        if scored:
            results.append(scored)
            print(f"  → {scored.get('score_pct',0):.1f}% | {scored.get('decision','')}")
        time.sleep(3)

    qualified = [r for r in results if r.get("score_pct", 0) >= MIN_SCORE_PCT]
    print(f"\nResults: {len(results)} scored | {len(qualified)} qualified (≥{MIN_SCORE_PCT:.0f}%)")

    # Log and email
    if results:
        log_to_sheets(results, vertical_name)
        send_email(results, vertical_config)
    else:
        print("No results to log or email")

    print(f"\nVertical pipeline complete — {vertical_name}")


if __name__ == "__main__":
    main()
