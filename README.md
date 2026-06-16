# Second Layer VC Pipeline

An automated sourcing and scoring system for seed-stage companies aligned with the **Second Layer investment framework** — investing in companies that solve problems *created by* dominant industry trends, not companies that are the trend itself.

---

## Second Layer Framework

> "Every dominant trend creates a second-order problem. We invest in the companies that solve it."

The Second Layer Approach seeks to identify the "yet to be understood" impacts of dominant industry trends, pinpointing areas of both opportunity and risk where investors should be focusing today.

| Step | Track | Description |
|------|-------|-------------|
| **1. Observe** | — | Identify dominant and fastest-growing industries |
| **2. Question** | **Opportunity (2a)** | What growth do they enable? |
| | **Risk (2b)** | What problems do they cause? |
| **3. Invest** | **Supplement (3a)** | Solutions that accelerate 2a growth |
| | **Mitigate (3b)** | Solutions that reduce risk from 2b |

---

## Verticals (V0–V20)

### Original Verticals (V0–V5)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V0** | Energy, Climate & Sustainability Tech | Renewable buildout + AI data center demand created site selection, interconnection, and financing bottlenecks that block deployment |
| **V1** | Data Privacy, Governance & Compliance | GDPR, state privacy laws, and enterprise data sprawl created compliance burden no internal team can manage manually |
| **V2** | Fintech, Payments & Financial Compliance | Fintech and crypto proliferation created AML, KYC, and sanctions compliance obligations every new platform must meet on day one |
| **V3** | Space, Ocean Tech & Advanced Navigation | Satellite cost collapse created orbital congestion, maritime detection gaps, and traffic management problems no legacy system was built for |
| **V4** | AI Governance, Safety & Responsible AI | Enterprise LLM adoption created evaluation, monitoring, and audit obligations no traditional QA tool addresses |
| **V5** | Biotech, Medtech & Life Sciences Compliance | FDA digitization and clinical AI adoption created regulatory documentation and validation workflows legacy CROs cannot scale |

### Split Verticals (V6–V11)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V6** | Supply Chain & Logistics | Reshoring, tariff volatility, and SBOM mandates created visibility and traceability requirements legacy ERPs cannot meet |
| **V7** | Legal Tech & Contract Intelligence | Enterprise AI adoption and contract velocity created review and litigation workflows law firms cannot staff manually |
| **V8** | Cybersecurity, Infrastructure & Operations | Cloud sprawl and AI-amplified threats created detection and response loads that overwhelm legacy SOC tools |
| **V9** | Insurance, Risk Management & Real Estate Tech | Climate risk, AI underwriting data, and construction tech adoption created risk modeling needs traditional insurers cannot price |
| **V10** | Healthcare & Interoperability | Medicare Advantage expansion and EHR fragmentation created navigation, prior authorization, and care coordination crises |
| **V11** | Agtech & Food Systems | Climate volatility, food traceability mandates, and precision agriculture data created tooling gaps small operators cannot bridge |

### AI Second Layer Verticals (V12–V15)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V12** | AI Security, Red-Teaming & Content Authenticity | Enterprise LLM deployment and deepfake proliferation created model security and content provenance requirements |
| **V13** | AI Agent Infrastructure & Tooling | Agentic AI adoption created authentication, payments, orchestration, and tool-calling bottlenecks |
| **V14** | AI Compute, Energy & Data Center Infrastructure | AI compute demand exploded faster than data center cooling, grid interconnection, and inference efficiency could scale |
| **V15** | Workforce Transition & AI-Augmented Services | AI adoption disrupted services labor markets faster than reskilling and copilot infrastructure could respond |

### Net-New Verticals (V16–V19)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V16** | Defense, Dual-Use & Export Compliance | Defense tech boom created ITAR, CMMC, and supply chain security requirements dual-use startups are structurally unequipped to handle |
| **V17** | Robotics & Physical Automation Enablement | Humanoid and warehouse robotics deployment created integration, orchestration, certification, and insurance gaps |
| **V18** | Aging Economy & Elder Care Infrastructure | Aging demographics and Medicare Advantage growth created care coordination and benefits navigation crises |
| **V19** | Post-Quantum Security & Cryptographic Migration | NIST PQC standards and federal migration mandates created mandatory cryptographic inventory and migration work |

### Consumer Vertical (V20)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V20** | Consumer Health & Wellness Brands | Health/wellness trend and functional food movement created consumer demand for better-for-you alternatives in legacy indulgence categories (snacking, beverages, personal care) that incumbents are structurally slow to serve |

---

## Pipeline Architecture

### Main Pipeline Sources

| Source | Frequency | Volume | Quality |
|--------|-----------|--------|---------|
| YC Companies (yc-oss API) | Per run | Recent batches (W23–S26) | High — curated founders |
| SEC Form D Filings | Per run | Keyword-matched | High — legally-mandated raise signal |
| TechCrunch | Per run | Keyword-matched | Medium — funding coverage |
| SBIR/STTR Awards | Per run | AI-filtered | High — pre-VC government grant signal |
| Hugging Face Trending | Per run | Big labs filtered out | Medium — pre-funding AI startup signal |
| Product Hunt | Per run | Daily leaders | Medium — launch-day product signal |
| HN Show HN | Per run | ~100 posts | Low — filter heavy |
| RSS Funding Feeds | Per run | 3–5 seed matches | Medium — funding signal |
| Claude Research | Per run | 6–8 candidates | High — framework-aligned |

### Vertical Pipeline Sources (V0–V20)

The vertical pipeline runs per-vertical and uses five free sources, each filtered by the vertical's keywords:

| Source | How it's filtered | Notes |
|--------|-------------------|-------|
| YC Companies | Vertical keywords matched against company text | Recent batches only |
| SEC Form D | Vertical keywords as full-text search query | Catches raises with no press coverage |
| TechCrunch | Vertical keywords + seed-stage terms | Venture/startups/seed-funding feeds |
| Vertical RSS | Sector-specific publications | 2–5 feeds per vertical |
| Claude Research | Vertical-specific search terms | Highest framework alignment |

> **Note on V20 (Consumer Health & Wellness Brands):** This vertical sources primarily through CPG-specific RSS feeds (FoodNavigator-USA, BevNET, Nosh, Beauty Independent, Food Dive) and Claude Research. YC, SEC Form D, and SBIR sources contribute minimally for consumer brands but do not require separate infrastructure.

All candidates pass a **funding verification step** (Claude fills in funding/stage for $0 candidates) before the three hard gates run.

### Scoring

#### 9-Factor Framework (Vertical Pipeline / Medtech / Hardware)

| # | Factor | Weight |
|---|--------|--------|
| 1A | Founder-Market Fit | 14% |
| 1B | Technical Differentiation | 11% |
| 1C | Founder Commitment | 10% |
| 2A | Product-Market Fit | 15% |
| 3A | Market Size (TAM) | 12% |
| 3B | Timing & Competition | 11% |
| 5 | Traction Quality | 10% |
| 6 | Capital Efficiency | 10% |
| 7 | Investor Signal | 7% |

#### 11-Factor Framework (Main Pipeline / SaaS / Fintech)

| # | Factor | Weight |
|---|--------|--------|
| 1A | Founder-Market Fit | 10% |
| 1B | Technical Execution | 8% |
| 1C | Founder Commitment | 7% |
| 2A | Early Product-Market Fit | 12% |
| 2B | Revenue Signals | 8% |
| 3A | Market Size (TAM) | 12% |
| 3B | Timing & Competition | 8% |
| 4 | Traction — Quantitative | 7% |
| 5 | Traction — Qualitative | 8% |
| 6 | Capital Efficiency | 10% |
| 7 | Investor Signal | 10% |

**Minimum score thresholds:** Pre-seed: 55% | Seed: 65% | Unknown: 60%

### Hard Gates (applied before scoring)

All three must pass or the company is excluded:

- **Stage:** Pre-seed, seed, or Series A only
- **Funding:** ≤ $15M total raised
- **Age:** Founded ≤ 5 years ago AND last round ≤ 24 months ago

---

## Google Sheet

**Sheet ID:** `102k3pj7JjEhSXWgyBS144mgHd93MZywoWVyjWIonX50`

| Tab | Contents |
|-----|----------|
| Pipeline | All candidates scoring above threshold from main pipeline runs |
| Vertical Pipeline | Candidates organized by vertical (V0–V20) |
| Vertical Reference | V0–V20 schema reference with Second Layer logic and example companies |
| Founder Pipeline | Direct founder sourcing and outreach tracking |
| Pipeline Archive | Historical pipeline runs |
| Company Pipeline | Extended company tracking |
| Empty (copy paste) | Template tab |

### Pipeline Headers (26 columns)

```
Date | Company | Stage | Total Raised | Vertical | Source | Second Layer Logic | Description | Passed Gates | Founders | 1A_FMF | 1B_Tech | 1C_Commit | 2A_PMF | 3A_TAM | 3B_Timing | 5_TrxQl | 6_CapEff | 7_Investor | Weighted % | Decision | Summary | Strengths | Risks | Website | LinkedIn
```

---

## Workflows

| Workflow | File | Schedule | Trigger |
|----------|------|----------|---------|
| Main Pipeline | `main_pipeline.yml` | Daily 12:00 UTC | Cron + manual |
| Vertical Pipeline | `vertical_pipeline.yml` | Daily 13:00 UTC | Cron + manual (index 0–20) |
| Test APIs | `test_apis.yml` | Manual | GitHub Actions |

---

## File Structure

```
/
├── sourcer.py              # Main sourcing logic (YC, SEC, TechCrunch, SBIR, HF, PH, HN, RSS, Claude)
├── vertical_pipeline.py    # Vertical pipeline runner (5 sources per vertical)
├── vertical_sources.py     # V0–V20 vertical schema (keywords, RSS feeds, search terms)
├── pipeline_utils.py       # Scoring, gates, sheet writing, funding verification
├── test_apis.py            # API credential diagnostic
├── .github/
│   └── workflows/
│       ├── main_pipeline.yml
│       ├── vertical_pipeline.yml
│       └── test_apis.yml
└── README.md
```

---

## Secrets Required

| Secret | Used By |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude Research sourcing, scoring, funding verification |
| `GOOGLE_CREDENTIALS_JSON` | Sheet read/write |
| `GOOGLE_SHEET_ID` | Target sheet |
| `GITHUB_TOKEN` | GitHub search source (optional) |

---

## Current Source Status

| Source | Status | Notes |
|--------|--------|-------|
| YC Companies | ✅ Working | yc-oss all.json filtered by vertical keywords + batch |
| SEC Form D | ✅ Working | EDGAR full-text search, no API key needed |
| TechCrunch | ✅ Working | Venture/startups/seed-funding feeds |
| SBIR/STTR | ✅ New | Government grant signal, keyword-filtered |
| Hugging Face | ✅ New | Trending AI orgs, big labs filtered out |
| Product Hunt | ✅ New | Daily leaders via RSS |
| RSS Funding | ✅ Working | 2–3 sector feeds per vertical |
| Claude Research | ✅ Working | 6–8 high-quality candidates/run |
| HN Show | ✅ Working | Main pipeline only |
| Crustdata | ❌ Removed | Retired June 2026 |
| GitHub Search | ⚠️ Skipped | Requires GITHUB_TOKEN secret |

---

## Investment Thesis

**Second Layer investing** identifies companies that solve problems created by dominant industry trends — not companies that are the trend itself.

The pipeline is designed to surface founders who:
1. Have deep domain experience in the problem they are solving
2. Are building infrastructure, not features
3. Are entering markets created by regulatory mandates, industry shifts, or structural complexity — not discretionary spend
4. Are capital efficient and founder-committed at the seed stage

*Built and maintained by Bryan Hanley — bryanhanleyvc.substack.com*
