# Second Layer VC Pipeline

An automated sourcing and scoring system for seed-stage companies aligned with the **Second Layer investment framework** — investing in companies that solve problems *created by* dominant industry trends, not companies that are the trend itself.

---

## Second Layer Framework

> "Every dominant trend creates a second-order problem. We invest in the companies that solve it."

| Layer | Example |
|-------|---------|
| **First Layer** | AI adoption explodes across enterprise |
| **Second Layer** | Governance gap, regulatory liability, and model drift → AI governance and validation platforms |

The pipeline identifies companies where a structural, technology, or regulatory shift has created a **new, unavoidable problem** — and a founder has built the infrastructure layer to solve it.

---

## Verticals (V0–V9)

| ID | Vertical | Dominant Trend | Second Layer Logic |
|----|----------|----------------|--------------------|
| **V0** | Energy, Climate & Sustainability | Energy transition and ESG regulatory expansion | The shift to renewables created grid complexity and carbon accounting mandates → ESG reporting automation, grid intelligence, clean energy operations software, and EV infrastructure became essential |
| **V1** | Data Privacy, Governance & Compliance | Data broker proliferation and regulatory expansion | 750+ data brokers openly trade personal data → GDPR, CCPA, CPRA, and expanding state privacy laws created compliance mandates → consumer data removal, PII engineering, and enterprise consent infrastructure became required |
| **V2** | Fintech, Payments & Financial Compliance | Global fintech and payments expansion | Fintech expanded financial access globally → regulatory burden grew proportionally → AML, KYC/KYB, sanctions screening, fraud prevention, and financial crime compliance became mandatory bottlenecks for every fintech and bank |
| **V3** | Space, Ocean Tech & Navigation | Commercial satellite and maritime proliferation | SpaceX drove launch costs down 95% → thousands of satellites in orbit, commercial maritime automation expanding → demand for earth observation intelligence, space cybersecurity, autonomous navigation, ground segment software, and space traffic management |
| **V4** | AI Governance, Safety & Responsible AI | Enterprise AI adoption at scale | 61% of VC went to AI in 2025 → enterprises deploying models at scale → governance gap, regulatory liability, bias drift, and LLM safety risk → AI governance, model validation, and responsible AI platforms |
| **V5** | Biotech, Medtech & Life Sciences | Healthcare digitization and FDA regulatory expansion | Healthcare AI and EHR proliferation created new clinical data pipelines → HIPAA complexity, FDA software regulation, and clinical trial digitization created compliance and validation bottlenecks → medtech software, clinical AI, and biotech ops platforms |
| **V6** | Supply Chain, Logistics & Legal Tech | Open source adoption and legal AI proliferation | Open source became ubiquitous → Log4Shell and SolarWinds proved supply chain risk → SBOM compliance, dependency scanning, and supply chain security became regulatory requirements. Simultaneously, legal AI made drafting accessible to non-lawyers → malpractice and compliance risk grew → contract intelligence and compliance-grade legal workflows became essential |
| **V7** | Cybersecurity, Infrastructure & Operations | Cloud adoption explosion | Cloud created multi-cloud complexity and expanding attack surfaces → CSPM, DevSecOps, SOC automation, supply chain security, and identity security became essential infrastructure for every enterprise |
| **V8** | Insurance, Risk Management & Real Estate | Digital transformation of financial and physical assets | Insurance digitization and construction tech adoption created new underwriting data and project complexity → claims automation, AI underwriting, construction permitting, and real estate risk platforms emerged as essential infrastructure |
| **V9** | Healthcare, Interoperability & Agtech | Healthcare digitization and food supply chain expansion | Healthcare digitized rapidly → EHR fragmentation and administrative burden grew → care navigation, prior authorization, billing, and interoperability became unsustainable bottlenecks. Simultaneously, global food supply chain complexity created demand for agtech, traceability, and food safety compliance platforms |

---

## Pipeline Architecture

### Sources

| Source | Frequency | Volume | Quality |
|--------|-----------|--------|---------|
| Crustdata Cache | Weekly refresh | ~75 companies | Medium — broad filter |
| YC Companies (yc-oss API) | Per run | W25/S25/W26/F25/X25 batches | High — curated founders |
| HN Show HN | Per run | ~100 posts | Low — filter heavy |
| RSS Funding Feeds | Per run | 3–5 seed matches | Medium — funding signal |
| Claude Research | Per run | 6–8 candidates | High — framework-aligned |

### Scoring

All candidates are scored against the **11-Factor Second Layer Framework**:

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

**Minimum score threshold: 65%**

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
| Pipeline | All candidates scoring ≥ 65% from main pipeline runs |
| Vertical Pipeline | Candidates scoring ≥ 65% organized by vertical (V0–V9) |
| Founder Pipeline | Direct founder sourcing and outreach tracking |
| Crustdata Cache - Main | Raw Crustdata output (75 companies/week) |
| Pipeline Archive | Historical pipeline runs |
| Company Pipeline | Extended company tracking |
| Empty (copy paste) | Template tab |

---

## Workflows

| Workflow | File | Schedule | Trigger |
|----------|------|----------|---------|
| Main Pipeline | `main_pipeline.yml` | Daily 12:00 UTC | Cron + manual |
| Crustdata Refresh | `crustdata_refresh.py` | Weekly | Cron |
| Test Sources | `test_sources.yml` | Manual | GitHub Actions |

---

## File Structure

```
/
├── sourcer.py              # Main sourcing logic (all sources)
├── pipeline_utils.py       # Scoring, filtering, sheet writing
├── crustdata_refresh.py    # Weekly Crustdata cache refresh
├── test_sources.py         # Source verification (no API keys needed)
├── .github/
│   └── workflows/
│       ├── main_pipeline.yml
│       ├── crustdata_refresh.yml
│       └── test_sources.yml
└── README.md
```

---

## Secrets Required

| Secret | Used By |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude Research sourcing, scoring |
| `CRUSTDATA_API_KEY` | Crustdata weekly refresh |
| `GOOGLE_SHEETS_CREDENTIALS` | Sheet read/write |
| `GITHUB_TOKEN` | GitHub search source (optional) |

---

## Current Source Status

| Source | Status | Notes |
|--------|--------|-------|
| Crustdata Cache | ✅ Working | 75 companies/run, endpoint fixed |
| YC Companies | ✅ Working | yc-oss all.json filtered by batch |
| RSS Funding | ✅ Working | 6 feeds, 3–5 seed matches/run |
| HN Show | ✅ Working | Low quality, filter heavy |
| Claude Research | ✅ Working | 6–8 high-quality candidates/run |
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
