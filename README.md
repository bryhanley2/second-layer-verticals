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

## Verticals (V0–V21)

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

### Thesis Vertical — Fund Focus (V21)

| ID | Vertical | Second Layer Logic |
|----|----------|--------------------|
| **V21** | AI Physical Infrastructure Software (Energy, Grid & Thermal) | AI compute demand is outpacing the energy, grid, and thermal buildout meant to sustain it; V21 sources asset-light software that unlocks, accelerates, and optimizes that buildout — not the buildout itself |

**V21 is the fund's core thesis vertical**, distinct from V0 (general energy/climate) and V14 (broader AI compute/data center infrastructure) in three ways:

- **Narrower scope:** four defined subsectors only — Siting & Permitting Intelligence, Interconnection & Grid Navigation, Financing/Transaction Infrastructure, Thermal/Cooling Optimization Software
- **Tighter stage discipline:** target funding range is **$1.8M–$4M** (genuine seed), not the $15M ceiling used elsewhere in the pipeline — see [V21 Funding Range](#v21-funding-range-tighter-than-other-verticals) below
- **Proprietary source architecture:** V21 is the only vertical with a `scrape_targets` field — see [Proprietary Sourcing Layer](#proprietary-sourcing-layer-v21-only) below

---

## Pipeline Architecture

> **Scope of this repo:** this repository is the **vertical pipeline** only
> (`vertical_pipeline.py`, per-vertical sourcing V0–V21). The broader
> **Main Pipeline** (`sourcer.py` / `main_pipeline.yml` — a single cross-industry
> daily run) lives in a **separate repository** and is not part of this codebase.
> The Main Pipeline section below is retained for context on the overall system;
> the `Pipeline` sheet tab it writes to is shared between both repos.

### Main Pipeline Sources *(separate repo — reference only)*

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

### Vertical Pipeline Sources (V0–V21)

The vertical pipeline runs per-vertical and uses these free sources, each filtered by the vertical's keywords:

| Source | How it's filtered | Notes |
|--------|-------------------|-------|
| YC Companies | Vertical keywords matched against company text | Recent batches only |
| SEC Form D | Vertical keywords as full-text search query | Catches raises with no press coverage |
| TechCrunch | Vertical keywords + seed-stage terms | Venture/startups/seed-funding feeds |
| Vertical RSS | Sector-specific publications | 2–5 feeds per vertical |
| Claude Research | Vertical-specific search terms | Highest framework alignment |
| YC Launch HN | Vertical keywords against the launch pitch | Last ~8 months of "Launch HN" posts, recent-batch only (`new_sources.py`) |
| Product Hunt | Vertical keywords against title + tagline | ~50 newest products; mostly noise outside consumer/AI verticals (`new_sources.py`) |
| VC Newsletters | Funding-headline extraction + vertical keywords | StrictlyVC, a16z, Newcomer, Not Boring, The Diff, … via the Vertical RSS parser |
| Scrape layer | Claude extraction from the vertical's `scrape_targets` + run-over-run diff | Specialist-fund portfolios / accelerator cohorts; 15 of 22 verticals (see **Proprietary Scrape Layer** below) |

YC Launch HN / Product Hunt / VC Newsletters run in STEP 1 unless `EXTRA_SOURCES=0`; the scrape layer unless `SCRAPE_LAYER=0`.

> **Note on V20 (Consumer Health & Wellness Brands):** This vertical sources primarily through CPG-specific RSS feeds (FoodNavigator-USA, BevNET, Nosh, Beauty Independent, Food Dive) and Claude Research. YC, SEC Form D, and SBIR sources contribute minimally for consumer brands but do not require separate infrastructure.

All $0-funding candidates pass a **multi-source funding verification step** before the three hard gates run (and V21 additionally runs a **post-enrichment size re-check** — see below):

1. **Crunchbase API** — only if `CRUNCHBASE_API_KEY` is set (`high` confidence)
2. **SEC EDGAR Form D** — the company's own filings, *strict* name match, fund/SPV entities rejected; sums `totalAmountSold` across filings (`medium` confidence, filing URL as the citation) — this is what catches the "labelled seed, actually raised $170M" case
3. **Claude** — with a hard source-citation requirement; returns null (never a guess) when it can't cite one

Every candidate carries a `_funding_checks` audit trail. A verified figure ships with its source URL; an unverified one ships with exactly what was tried (`unverified (checked crunchbase: no key; sec form d: no filing; claude: no source)`) so the analyst knows what to check by hand.

**Then a confirmation pass** (`confirm_funding_report`, STEP 1c) cross-checks each verified figure:

- **Cross-source agreement** — if two passes produced figures that disagree by >1.5× and >$1M: trust the SEC filing if there is one (and flag), otherwise clear the figure back to unverified
- **Stage/amount plausibility** — "pre-seed" + >$5M or "seed" + >$12M → `STAGE_MISMATCH`, confidence downgraded so it doesn't read as a clean seed number
- **Staleness** — figure's round date older than 15 months → `STALE` advisory (a newer round may have raised the real total)

Flags show in the digest (`[!] labelled 'seed' but $14M verified; figure is ~19 months old`). Only *then* does the post-enrichment size re-check (`verify_size_post_enrichment`) apply the $10M hard cap.

### Proprietary Scrape Layer

The sources above are press-and-announcement based — every fund scraping YC and TechCrunch sees the same companies. Each vertical with a `scrape_targets` list also gets a scrape pass that surfaces companies *before* they appear in venture press, by diffing specialist-fund portfolios / accelerator cohorts / program awardee lists run over run.

**Coverage (15 of 22 verticals, ~55 targets):**

| Vertical | Example targets |
|---|---|
| V0 Energy/Climate | Congruent, Lowercarbon, Clean Energy Ventures, EIP |
| V2 Fintech | QED, Nyca, Commerce Ventures |
| V3 Space | Space Capital, Seraphim |
| V5 Biotech/Medtech | IndieBio, Nucleate, Petri |
| V6 Supply Chain | Dynamo, Interlace, 4DX |
| V8 Cybersecurity | Ten Eleven, YL Ventures, ForgePoint, NightDragon, SYN |
| V9 Insurance/RE | Fifth Wall, MetaProp |
| V10 Healthcare | Rock Health, .406 Ventures |
| V11 Agtech | AgFunder, S2G, Fall Line |
| V13 AI Agents | Air Street, Basis |
| V16 Defense | a16z American Dynamism, 8VC, Decisive Point |
| V17 Robotics | Eclipse, Lux |
| V18 Elder Care | Primetime Partners, Ziegler Link-Age |
| V20 Consumer CPG | XRC Labs, Springdale |
| **V21** AI Physical Infra | DOE AI4IX/i2X, Powerhouse, Stepchange, MCJ, NYSERDA, Third Derivative, Elemental, Greentown, ERCOT, PJM (17 targets) |

**Proven results (V21):** Glacian Technologies (Penn State tech-transfer), GridBoost / ContractPower (DOE AI4IX teaming list) — none would have surfaced through the standard sources.

**How `source_vertical_scrape()` works:**

1. Fetch each `scrape_target` — static `requests` GET first, then a **headless Chromium render (Playwright)** when the static result is a JS shell.
2. Claude extracts operating-company names from each page (skips nav, fund names, report titles; text-only, no inference; the vertical's name + keywords steer it).
3. `passes_scrape_filter()` drops rejects by keyword — a common set (exits, public companies, law firms, SPVs) plus per-vertical lists (software verticals reject hardware/manufacturing; V5 rejects drug-pipeline companies; V20 rejects B2B software). Block/parked pages are skipped before spending a Claude call.
4. Diff against the **`Scrape Seen`** sheet tab — only names *not seen in a prior run* enter the pipeline. Every surfaced name is recorded immediately, so a company that later fails the gates isn't re-extracted. First run per vertical is capped at `SCRAPE_MAX_NEW` (default 50).

Survivors flow through the normal gates → funding verification → Second Layer filter → 9-factor scoring. Disable the layer with `SCRAPE_LAYER=0`, the headless fallback with `SCRAPE_HEADLESS=0` (legacy `V21_SCRAPE*` names still work).

**Headless fetch** needs `playwright` + `playwright install chromium` (the workflow does both, cached). Verified live: 38/38 non-V21 targets + 15/17 V21 targets return usable content; parked/bot-blocked ones (Powerhouse, Urban Future Lab) are skipped gracefully.

### V21 Funding Range (Tighter Than Other Verticals)

V21 enforces a stricter funding band than the pipeline-wide hard gates. Every vertical's candidates must clear the $15M/$10M ceilings below, but V21 candidates are further tiered by a **post-enrichment size filter** (`verify_size_post_enrichment()` in `pipeline_utils.py`):

| Status | Range | Action |
|---|---|---|
| `REJECT` | > $10M verified | Removed from pipeline |
| `ABOVE_RANGE` | $4M–$10M | Kept, flagged in sheet |
| `IN_RANGE` | $1.8M–$4M | Ideal — genuine seed |
| `BELOW_RANGE` | < $1.8M | Kept, flagged as earliest-stage |
| `UNVERIFIED` | No confirmed figure | Kept, flagged for manual check |

This exists because the pipeline's original hard gate runs *before* funding enrichment — a company can pass on a "seed" label alone when its real funding figure is still $0/missing, then turn out to have raised far more once enriched (e.g., a company labeled seed that had actually raised $68M). The post-enrichment filter re-checks size once real data exists and removes anything that slipped through on a missing-data technicality.

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

**Scoring is a ranking, not a gate.** Every candidate that passes the hard gates + the Second Layer filter is scored and **written to the sheet, sorted by score**, as long as it clears `WRITE_FLOOR_PCT` (default 45 — below that the data is too thin to be worth a reviewer's time). `MIN_SCORE_PCT` (default 64) tags a row "recommended" via its Decision label; it doesn't filter.

**Two enrichment passes feed the scorer:**
1. Every Second Layer survivor's own **website text** (`/`, `/about`, `/product`, `/solutions`).
2. The top `ENRICH_TOP_N` (default 3) by initial score get one **web-search Claude call** for sourced founders / funding / traction, then are **re-scored** (`DEEP_ENRICH=0` to skip). ~$0.20/run.

Decision tiers: `STRONG YES` ≥80 · `YES — deep dive` ≥70 · `REVIEW — recommended` ≥64 · `WATCH — needs verification` ≥55 · `BACKLOG — thin data` ≥45.

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
| Vertical Pipeline | Candidates organized by vertical (V0–V21) |
| On-Demand Pipeline | Candidates from free-text `INDUSTRY_QUERY` runs (auto-created) |
| Vertical Reference | V0–V21 schema reference with Second Layer logic and example companies |
| Founder Pipeline | Direct founder sourcing and outreach tracking |
| Pipeline Archive | Historical pipeline runs |
| Company Pipeline | Extended company tracking |
| Scrape Seen | Run-over-run state for the scrape layer (auto-created) |
| Empty (copy paste) | Template tab |

### Pipeline Headers (26 columns)

```
Date | Company | Stage | Total Raised | Vertical | Source | Second Layer Logic | Description | Passed Gates | Founders | 1A_FMF | 1B_Tech | 1C_Commit | 2A_PMF | 3A_TAM | 3B_Timing | 5_TrxQl | 6_CapEff | 7_Investor | Weighted % | Decision | Summary | Strengths | Risks | Website | LinkedIn
```

---

## Workflows

| Workflow | File | Schedule | Trigger |
|----------|------|----------|---------|
| Vertical Pipeline | `vertical_pipeline.yml` | **Manual only** (no cron) | "Run workflow" (`vertical_index` or `industry_query`) + `repository_dispatch` |
| Test APIs | `test_apis.yml` | Manual | "Run workflow" |

*(The Main Pipeline workflow runs from its own repo. To re-add a daily schedule here, uncomment the `schedule:` block in `vertical_pipeline.yml`.)*

---

## Cost Controls

Every run costs Anthropic API tokens (rough estimate: ~$0.50 for a typical vertical, ~$1 for V21). Levers, set as GitHub **repo variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Default | Effect |
|---|---|---|
| `PIPELINE_MODEL` | `claude-opus-4-7` | Judgement calls (scoring, Second Layer, funding verify). `claude-sonnet-5` ≈ 2.5× cheaper. |
| `PIPELINE_MODEL_EXTRACT` | `claude-haiku-4-5` | Scrape name-extraction (mechanical). Already the cheap model. |
| `RESEARCH_MAX_QUERIES` | `12` | Cap on Claude research calls/run (V21 defines ~24 — the rest are skipped unless you raise this). Set `4` for V21 — the research queries overlap heavily. |
| `MIN_SCORE_PCT` | `64` | Score at/above which a written row is tagged "recommended". Does not filter. |
| `WRITE_FLOOR_PCT` | `45` | Below this a candidate is dropped, not written. |
| `DEEP_ENRICH` | `1` | `0` skips the web-search + re-score pass on the top candidates. |
| `ENRICH_TOP_N` | `3` | How many top candidates get the deep research pass (~$0.06 each). |
| `SCRAPE_LAYER` | `1` | `0` disables the whole scrape layer. |
| `SCRAPE_HEADLESS` | `1` | `0` skips the Chromium fallback (also cuts ~1–2 min of CI per run). |
| `SCRAPE_RETRY_DAYS` | `60` | A scrape company that keeps soft-failing is retried each run until it's this old, then dropped. |
| `EXTRA_SOURCES` | `1` | `0` disables YC Launch HN / Product Hunt / VC newsletters (free APIs, but add candidates → more scoring calls). |

Scoring and Second Layer evaluation stay on the capable model regardless — candidate quality is not traded for cost there.

**Scrape page cache** — an unchanged portfolio page reuses its last extraction instead of calling Claude again (`Scrape Cache` sheet tab, keyed by page-content hash). A "nothing new" run is nearly free.

**Pre-scoring enrichment** — before the 9-factor score, each Second Layer survivor's own website (`/`, `/about`, `/product`, `/solutions`) is fetched and fed to the scorer, so it judges on real material rather than a one-line blurb.

**Scrape retry** — the `Scrape Seen` tab now carries a `Status`. A company is marked `done` (never re-surfaced) only when it's **written to the sheet** or **hard-rejected** (over the funding cap, too old). One that just scored 55–63% stays `pending` and is re-tried on the next run of that vertical.

## On-Demand Pipeline (any industry)

Instead of one of the 22 predefined verticals, the pipeline can be run against a
**free-text industry or theme**. Claude synthesizes a vertical config for it —
name, Second Layer framing, 12–18 keywords, Claude-research search terms, and
2–5 candidate RSS feeds (each fetched and parsed; hallucinated feeds are dropped).
The full pipeline then runs for that synthesized vertical and writes to a separate
**`On-Demand Pipeline`** sheet tab.

**Ways to trigger:**

| How | Command / payload |
|---|---|
| Locally | `INDUSTRY_QUERY="precision fermentation" python vertical_pipeline.py` |
| GitHub UI | Run *Vertical Pipeline* → fill in **industry_query** |
| API / app | `repository_dispatch` with `event_type: run-industry-pipeline`, `client_payload: { "industry_query": "..." }` |

`INDUSTRY_QUERY` overrides `VERTICAL_INDEX`. The V21 scrape layer is skipped
(synthesized verticals have no `scrape_targets`); every other source runs.

---

## Outreach Digest

After scoring, the top `DIGEST_TOP_N` (default 10) candidates get a
**website-only** contact lookup (`contact_enrich.py`): fetch the company site's
home / contact / about / team pages and pull the best public email
(`founders@` > `team@` > `hello@` > `info@` …, on-domain preferred) plus a
company/founder LinkedIn URL if one is linked. **No LinkedIn scraping, no paid
APIs, no email-guessing.** Email hit rate is realistically ~40–60% — many
startups only expose a form, in which case the digest says so.

The digest (name, score, decision, summary, founders, Second Layer logic,
strengths/risks, website, email, LinkedIn) is emailed to `EMAIL_RECIPIENT`.
Enriched website/LinkedIn values are also written back to the sheet row.
Set `ENRICH_CONTACTS=0` to skip the lookup.

---

## File Structure

```
/
├── vertical_pipeline.py    # Vertical pipeline runner (sources 1–7 per vertical)
├── vertical_sources.py     # V0–V21 vertical schema (keywords, RSS feeds, search terms, V21 scrape targets)
├── new_sources.py          # YC Launch HN + Product Hunt sources, VC newsletter feed list
├── contact_enrich.py       # Website-only outreach lookup (public email + LinkedIn) for the digest
├── pipeline_utils.py       # Model constant, gates, scoring, funding verification, sheet I/O, LLM-error tracking
├── test_apis.py            # API credential diagnostic
├── sheets_logger_py        # Legacy alternate sheet writer — not wired in
├── .github/
│   └── workflows/
│       ├── vertical_pipeline.yml
│       └── test_apis.yml
└── README.md
```

`sourcer.py` and `main_pipeline.yml` belong to the separate Main Pipeline repo.

---

## Secrets Required

| Secret | Used By |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude Research sourcing, scoring, funding verification |
| `GOOGLE_CREDENTIALS_JSON` | Sheet read/write |
| `GOOGLE_SHEET_ID` | Target sheet |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `EMAIL_RECIPIENT` | Outreach digest email (optional — skipped if unset) |
| `CRUNCHBASE_API_KEY` | Funding verification pass 1 (optional — SEC + Claude run without it) |
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
| YC Launch HN | ✅ New | Recent "Launch HN" posts via HN Algolia, keyword + recent-batch filtered |
| Product Hunt | ✅ New | ~50 newest products via Atom feed, keyword-filtered; strong only for consumer/AI verticals |
| VC Newsletters | ✅ New | StrictlyVC / a16z / Newcomer / Not Boring / The Diff via the funding-headline RSS parser |
| RSS Funding | ✅ Working | 2–3 sector feeds per vertical |
| Claude Research | ✅ Working | 6–8 high-quality candidates/run |
| HN Show | ✅ Working | Main pipeline only |
| GitHub Search | ⚠️ Skipped | Requires GITHUB_TOKEN secret |
| Scrape Layer | ✅ Live (static + headless) | `source_vertical_scrape()` — 15/22 verticals with `scrape_targets`; static/Playwright fetch + Claude extraction + filter + run-over-run diff via the `Scrape Seen` tab. |

**Funding data integrity (Aug 2026 fix):** the Claude Research sourcing step no longer asks the model to produce funding figures directly — it fabricated plausible-but-wrong numbers (e.g. recycling one company's raise onto another). Funding is now sourced only through the verification pass, which requires a citable source or returns null. Companies with unconfirmed funding are flagged `(UNVERIFIED)` in the sheet rather than shown with a bare number.

---

## Investment Thesis

**Second Layer investing** identifies companies that solve problems created by dominant industry trends — not companies that are the trend itself.

The pipeline is designed to surface founders who:
1. Have deep domain experience in the problem they are solving
2. Are building infrastructure, not features
3. Are entering markets created by regulatory mandates, industry shifts, or structural complexity — not discretionary spend
4. Are capital efficient and founder-committed at the seed stage

*Built and maintained by Bryan Hanley — bryanhanleyvc.substack.com*
