# Second Layer Vertical Research Pipeline

An automated seed-stage startup sourcing system built on the **Second Layer** investment thesis — finding companies that exist because a dominant industry trend created a downstream problem.

This pipeline runs one industry vertical per day on a 10-day rotation, sources pre-seed and seed-stage companies from multiple channels, scores them against a proprietary evaluation rubric, logs results to Google Sheets, and delivers a daily email digest.

> **Related:** [second-layer-vc-pipeline](https://github.com/bryhanley2/second-layer-vc-pipeline) — the main daily sourcing pipeline across all verticals simultaneously.

---

## How It Works

Each day the pipeline:

1. Selects today's vertical based on `day_of_year % 10`
2. Sources candidates from three channels — Claude AI research, vertical-specific RSS feeds, and YC Algolia
3. Deduplicates and filters out previously seen companies
4. Scores up to 15 companies against the Second Layer rubric
5. Logs all results to the **Vertical Pipeline** tab in Google Sheets
6. Emails a digest with scores, decisions, and Second Layer logic

---

## The 10 Verticals

Each vertical maps to a specific dominant industry trend and the downstream investment opportunities it creates.

| Index | Vertical | Dominant Trend | Second Layer Logic |
|-------|----------|----------------|-------------------|
| **0** | Space & Defence AI | Commercial satellite proliferation | SpaceX drove launch costs down 95% → thousands of satellites in orbit → demand for earth observation intelligence, space cybersecurity, ground segment software, and space traffic management |
| **1** | AI Governance & Model Risk | Enterprise AI adoption at scale | 61% of VC went to AI in 2025 → enterprises deploying models at scale → governance gap, regulatory liability, and bias drift → AI governance and model validation platforms |
| **2** | Fintech Compliance & AML | Global fintech expansion | Fintech expanded financial access globally → regulatory burden grew proportionally → AML, KYC/KYB, sanctions screening, and financial crime compliance became mandatory bottlenecks |
| **3** | Healthcare Navigation & Clinical AI | Healthcare digitization and EHR proliferation | Healthcare digitized rapidly → EHR fragmentation and administrative burden grew → clinical documentation, prior auth, care navigation, and billing became unsustainable bottlenecks |
| **4** | Cybersecurity & Cloud Security | Cloud adoption explosion | Cloud created multi-cloud complexity and expanding attack surfaces → CSPM, DevSecOps, supply chain security, and identity security became essential infrastructure |
| **5** | Legal AI & Contract Risk | Legal AI adoption | Legal AI made drafting accessible to non-lawyers → malpractice and compliance risk grew → contract intelligence and compliance-grade legal workflows became essential |
| **6** | Data Privacy & PII | Data broker proliferation and regulatory expansion | 750+ data brokers openly trade personal data → GDPR, CCPA created compliance mandates → consumer data removal and enterprise privacy engineering became required infrastructure |
| **7** | Supply Chain & SBOM Security | Open source adoption | Open source became ubiquitous → Log4Shell and SolarWinds proved supply chain risk → SBOM compliance, dependency scanning, and supply chain security became regulatory requirements |
| **8** | Consumer Fintech & Personal Finance | Fintech expansion and embedded finance | Fintech expanded credit and payments to millions → complexity, debt traps, and financial confusion grew → personal finance management, debt navigation, and financial literacy tools emerged |
| **9** | Climate Tech & Energy Transition | Energy transition and ESG regulatory expansion | Energy transition created grid complexity and carbon accounting mandates → ESG reporting automation, grid intelligence, and clean energy operations software became essential |

---

## Scoring Rubric

Companies are scored across 9 early-stage factors. Factors 2B (Revenue) and 4 (Quantitative Traction) are excluded — these metrics are rarely observable at pre-seed/seed and should not penalise early companies.

| Factor | Weight | Description |
|--------|--------|-------------|
| 1A Founder-Market Fit | 14% | Prior domain expertise, relevant background, prior exits |
| 1B Technical Differentiation | 11% | Working product, prototype, or differentiated approach |
| 1C Commitment | 10% | Full-time vs part-time, recent departure from prior role |
| 2A PMF Signals | 15% | Pilots, waitlists, early users, organic interest |
| 3A TAM | 12% | Total addressable market size |
| 3B Timing | 11% | Regulatory catalysts, structural tailwinds, competitive window |
| 5 Qualitative Traction | 10% | Accelerators, press, named pilots, awards |
| 6 Capital Efficiency | 10% | Capital-light model vs hardware-intensive |
| 7 Investor Quality | 7% | YC, top-tier VC, notable angels |

**Decision thresholds:**
- ≥ 85% → ★★★★★ Strong Yes
- ≥ 75% → ★★★★ Yes
- ≥ 65% → ★★★ Deep Dive
- ≥ 55% → ★★ Probably Pass
- < 55% → ★ Hard Pass

---

## Setup

### Prerequisites

- Python 3.11+
- Anthropic API key
- Gmail account with App Password enabled
- Google Cloud service account with Sheets API access
- Google Sheet with the service account email granted Editor access

### Installation

```bash
git clone https://github.com/bryhanley2/second-layer-verticals
cd second-layer-verticals
pip install anthropic requests beautifulsoup4 google-auth google-auth-httplib2 google-api-python-client
```

### Environment Variables

Create a `.env` file in the root or set these as GitHub Secrets:

```
ANTHROPIC_API_KEY=sk-ant-...
EMAIL_SENDER=your@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENT=your@gmail.com
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEET_ID=your_sheet_id_here
MIN_SCORE_PCT=65
```

### Run Manually

```bash
python vertical_pipeline.py
```

To force a specific vertical, temporarily override the index in `main()`:

```python
vertical_config = VERTICALS[0]  # Force Space & Defence AI
```

### GitHub Actions (Automated)

The pipeline runs automatically via `.github/workflows/vertical_pipeline.yml` every day at **8am EST**, one hour after the main pipeline.

To trigger manually: Actions → Run Vertical Pipeline → Run workflow

You can also pass a vertical index (0–9) via the `vertical_override` input to force a specific vertical on demand.

---

## Output

### Google Sheets

Results log to the **Vertical Pipeline** tab with the following columns:

`Date | Vertical | Company | Stage | Raise | Score % | Decision | Second Layer Logic | What They Do | Key Strength | Key Weakness | Source`

### Email Digest

Daily email with subject: `[Vertical Pipeline] {Vertical Name} — {N} qualified | {Date}`

Includes a full scored table with colour-coded rows — green for Yes and above, yellow for Deep Dive, white for below threshold.

---

## The Second Layer Thesis

The Second Layer approach to venture investing asks a second-order question about every dominant industry trend:

> *AI is the trend. What does AI make inevitable downstream?*

**Step 1 — Observe:** What industries are most dominant today? What is growing fastest?

**Step 2 — Question:** What opportunities does this create? What risks does this create?

**Step 3 — Invest:** What solutions supplement those opportunities? What solutions mitigate those risks? These are the investments.

The Second Layer is not compliance tech investing. It is a sourcing logic — a systematic way of finding the companies that dominant trends make inevitable, before the broader market recognises them as a category.

---

## Architecture

```
vertical_pipeline.py
│
├── VERTICALS[]          — 10 vertical configs (keywords, RSS feeds, Claude prompt)
│
├── source_claude_vertical()   — Claude Haiku research per vertical
├── source_rss()               — Vertical-specific RSS feeds
├── source_yc_vertical()       — YC Algolia keyword search
│
├── score_company()            — Second Layer rubric scoring via Claude Haiku
├── log_to_sheets()            — Google Sheets logging to Vertical Pipeline tab
└── send_email()               — HTML digest email
```

---

## Related Projects

- **[second-layer-vc-pipeline](https://github.com/bryhanley2/second-layer-vc-pipeline)** — Daily cross-vertical sourcing pipeline
- **[Second Layer Substack](https://bryanhanleyvc.substack.com)** — Investment thesis and company deep dives
- **[bryanhanleyvc.com](https://bryanhanleyvc.com)** — Second Layer thesis and sourcing framework

---

*Built by Bryan Hanley | Second Layer VC | bryanhanleyvc.com*
