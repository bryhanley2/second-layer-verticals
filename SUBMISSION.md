# Venture Institute submission — an AI-run seed-stage sourcing engine

**Bryan Hanley** · September 2026

- Live site: <https://bryanhanleyvc.com>
- Public thesis map: <https://bryanhanleyvc.com/map>
- Pipeline repo: `github.com/bryhanley2/second-layer-verticals`
- Web app repo: `github.com/bryhanley2/second-layer-web`

---

## The challenge

> Builders should vibecode a standalone web application that connects to an AI
> agent to complete a task related to VC dealflow or fundraising.

## What I built

A two-part system for a seed-stage investment thesis I call the **Second Layer
Approach**: back the companies solving the problems a dominant trend *creates*,
not the companies that *are* the trend.

1. **The engine** — a pipeline (Python, GitHub Actions, manual-trigger only) that
   sources seed-stage companies from specialist fund portfolios, SEC filings,
   accelerator cohorts, and sector press; verifies each company's funding against
   citable sources or marks it unverified; filters out anything that fails the
   thesis or isn't a real operating company; and scores what survives against a
   nine-factor rubric.

2. **The cockpit** — a React web application (`bryanhanleyvc.com`, Vercel) with a
   public "Second Layer Map", a private ranked dealflow board, a watchlist that
   re-checks promising companies for movement between runs, and a **live AI agent
   that assesses any company you name against the thesis, with web search and
   cited sources**.

The machine proposes; a human decides. No investment call is automated.

## How AI was used to build it

The entire system was built with AI as the engineering surface — not a chat
assistant, but the tool that wrote and revised the code across ~25 reviewed
feature branches and pull requests. Every merge is visible in the repo history.
The AI also runs *inside* the product: it is the judgement layer of the pipeline
(scoring, thesis evaluation, funding verification) and the interactive agent on
the site.

---

## Selected code

### 1. The thesis test — and a hard filter for non-companies

Before anything is scored, each candidate is put to the thesis and to an
existence check. A believable description is not enough; funds, accelerators, and
government programs are rejected outright.

```python
# pipeline_utils.py — evaluate_second_layer_fit()
prompt = f"""Evaluate Second Layer investment thesis fit.

Second Layer = company solves problems CREATED BY a dominant trend, NOT a
company that IS the trend.

FIRST: is this an operating, venture-backable company? Answer NO if it is a
venture fund, accelerator/incubator, government program or office, partnership
intermediary, nonprofit, industry association/consortium, standards body, or
research lab. If NO, respond with exactly: 0|NOT-A-COMPANY: <what it is>

Otherwise rate 1-3:
1 = Fails (IS the trend itself)
2 = Borderline/unclear
3 = Strong Second Layer fit
"""
# ...
except Exception as e:
    record_llm_error(f"Second Layer eval for {candidate.get('name')}", e)
    # Fail CLOSED: a failed eval scores 0, never a default that lets it through.
    return 0, "Second Layer eval failed (LLM error) — excluded"
```

### 2. Three deterministic gates

Stage, funding size, and recency are checked in code — not by the model — so the
thesis boundaries ($10M cap, seed/pre-seed only, ≤5 years old) can't drift.

```python
# pipeline_utils.py
def passes_stage_gate(candidate):
    stage = str(candidate.get("last_funding_round") or candidate.get("stage")).lower()
    if any(s in stage for s in ("series a", "series b", "series c")):
        return False, f"stage '{stage}' is Series A or later — seed/pre-seed only"
    ...

def passes_funding_gate(candidate):
    total = safe_float(candidate.get("total_funding_usd", 0))
    if total > MAX_TOTAL_FUNDING:          # $10M
        return False, f"total funding ${total:,.0f} exceeds the cap"
    ...

def passes_age_gate(candidate):
    if founded_year and (this_year - founded_year) > MAX_COMPANY_AGE_YEARS:  # 5
        return False, f"founded {founded_year}, too old"
```

### 3. An anchored nine-factor scoring rubric

The scorer is given an explicit 1-to-10 definition for every factor and told to
score missing evidence as a negative, not a neutral. Weighted, the score becomes
a ranking — it doesn't gate.

```python
# pipeline_utils.py — score_candidate() prompt (excerpt)
"""Score each factor 1-10 using the anchors. If the evidence for a factor is
genuinely missing, score it 4 (not 5) and say so in RISKS — thin data is a
real negative at seed, not a neutral. Do not invent specifics.

1A. Founder-Market Fit — 9: founder built/operated the exact system this
   replaces. 6: adjacent-domain operator. 3: no stated relevant background.
2A. Product-Market Fit — 9: named paying customers or a described pipeline.
   6: live product, design partners. 3: pre-product. 1: idea stage.
3B. Timing — 9: a specific mandate, deadline, or structural shift makes this
   urgent NOW (name it). 6: strong tailwind, no hard catalyst. 3: "someday".
..."""

FACTOR_WEIGHTS = {"1A":.14, "1B":.11, "1C":.10, "2A":.15,
                  "3A":.12, "3B":.11, "5":.10, "6":.10, "7":.07}

def decision_from_score(pct):
    if pct >= 80: return "★★★★★ STRONG YES"
    if pct >= 70: return "★★★★ YES — deep dive"
    if pct >= 64: return "★★★ REVIEW — recommended"
    if pct >= 55: return "★★ WATCH — needs verification"
    return "★ BACKLOG — thin data"
```

### 4. Funding verified, never guessed

Every `$0` company runs a four-pass check — Crunchbase, then its own SEC Form D,
then its website, then a chunked cross-check by the model. A figure carries a
source and a confidence level, or it is stamped `UNVERIFIED`. A confirmation pass
then flags conflicts, stage mismatches, and stale figures.

```python
# vertical_pipeline.py — verify_zero_funding() flow
# Pass 1  Crunchbase (if key present)
# Pass 1b SEC EDGAR Form D — most-recent filing only, sanity caps, fund-entity filter
# Pass 1c the company's own site: "raised $Xm seed round"
# Pass 2  a chunked model cross-check, brace-trimmed JSON parse
# Anything still unconfirmed -> _funding_unverified = True  (shown as UNVERIFIED)
```

### 5. Anti-hallucination discipline

The scorer is explicitly forbidden from inventing founder names — a real failure
mode when a model completes a plausible-sounding bio.

```python
# pipeline_utils.py — the FOUNDERS instruction
"""FOUNDERS: If you do not know the specific founder names from a verifiable
source, write "UNVERIFIED — needs manual lookup" instead of guessing. NEVER
fabricate names like "Eric Ness" when the actual co-founder is "Eric Ryan".
NEVER complete the pattern of a plausible-sounding bio."""
```

Companies that end a run with unverified founders, no real funding, and no
traction are routed to the watchlist — never the board.

### 6. Longitudinal tracking — cheap signals, escalate only on a hit

Companies that clear the thesis but aren't ready are re-checked every run for
movement. The checks are free; a model call fires only when a signal lands.

```python
# vertical_pipeline.py — recheck_watchlist()
# 1. a new / larger SEC Form D filing
# 2. funding language on the company's own site
# 3. homepage content-hash changed since last check
# 4. careers-page job count grew by >= 3
# 5. fresh Google News RSS for the company name
# -> only if >=1 fired: ONE web-search model call to confirm what changed
#    and whether the company has raised past seed
```

### 7. The public map is curated, not a data dump

The pipeline classifies scored companies into a trend's problem layers, but only
above a real score, capped per layer, with a manual `Hide` override that survives
re-runs.

```python
# vertical_pipeline.py — build_second_layer_map()
MAP_MIN_SCORE = 62     # only companies above a real quality score go public
MAP_PER_LAYER = 6      # cap each layer, highest score first
# a manual "Hide" column in the sheet drops a row from the public page,
# and the flag is preserved across pipeline re-runs (matched by company name)
```

### 8. The web-app agent

The site's "Check a company" feature is a small autonomous agent: given a
company, it runs its own web searches in a loop and returns a structured thesis
assessment with sources.

```typescript
// api/company-check.ts (Vercel serverless)
const tools = [{ type: 'web_search_20260209', name: 'web_search', max_uses: 4 }];
let resp = null;
for (let i = 0; i < 4; i++) {                 // allow pause_turn continuations
  resp = await client.messages.create({ model: MODEL, max_tokens: 1400, tools, messages });
  if (resp.stop_reason !== 'pause_turn') break;
  messages.push({ role: 'assistant', content: resp.content });
}
// -> { is_operating_company, is_second_layer, current_stage,
//      total_raised_usd, latest_round, founders, traction, take, sources[] }
```

---

## Guardrails, in one place

| Risk | Control |
|---|---|
| Model invents a company | thesis test + existence check; unverifiable companies never reach the board |
| Model invents founders | explicit "mark UNVERIFIED, never guess" instruction |
| Wrong funding figure | 4-pass verification; cited or stamped unverified; conflict/stale flags |
| Thesis drift | stage / size / age enforced in deterministic code |
| Silent failure | every model call wrapped; systemic failures turn the run red |
| Public page overclaims | curated to a score threshold plus a human `Hide` review |

## By the numbers

The weekend version of "AI VC sourcing" is ~200 lines: pull Crunchbase and press
RSS, ask a model to score each company 1–10, write a sheet. What's actually here:

| | |
|---|---|
| Pipeline code | ~4,300 lines of Python, ~110 functions, 6 modules |
| Git history | 110 commits · 12 merged PRs · 58 branches · first commit April 2026 |
| Verticals | 22, each with its own keyword set, feeds, and thesis framing |
| Sourcing keywords | 244 hand-tuned |
| Curated RSS feeds | 51 (validated — hallucinated feeds dropped) |
| **Proprietary scrape targets** | **55** — specialist fund portfolios, DOE program pages, RTO/ISO market-participant registries, accelerator cohorts (15 verticals) |
| Distinct data sources | 9 |
| **Reject-filter keywords** | **102** — each tuned from a real bad row, to strip funds, accelerators, labs, and programs |
| Funding verification | 4 independent passes + 2 reconciliation passes |
| Scoring | 9 weighted factors, explicit 1–10 anchors each |
| Deterministic gates | 3 (stage, size, age) |
| Persistent state | 8 Google Sheet tabs (output, watchlist + cache, scrape-seen + cache, target ideas, map) |
| Resilience | 81 try/except blocks; fail-closed scoring; loud systemic-failure detection |
| Web app | ~1,700 lines TS/TSX · 3 serverless functions · 5 pages |

What separates it from a quick build:

1. **The sourcing surface is domain knowledge, not a data feed.** The 55 targets
   are specific places (a DOE AI-interconnection program page, ERCOT's
   market-participant registry, a specialist fund's portfolio) where seed-stage
   companies appear *before* venture press. Each needs a headless browser, model
   extraction, a run-over-run diff, and a content-hash cache.
2. **Funding is verified four ways, not trusted.** SEC EDGAR full-text search →
   `primary_doc.xml` parsing → fund-entity filtering → most-recent-filing logic →
   cross-source reconciliation. (The pipeline once summed a company's filings to
   "$5.5 billion" — that is the bug this catches.)
3. **The 102 reject keywords** are the difference between a list that is 30% funds
   and labs and one that is 95% operating companies.
4. **The failure engineering only exists because it ran dozens of times** —
   brace-trimmed JSON parsing for truncated batches, the empty-env-var bug,
   fail-closed scoring, the workflow-turns-red check.
5. **58 branches** means it has been argued with against real output, not
   assembled once.

The model call is the commodity. The moat is the sourcing surface, the
verification discipline, the encoded thesis, and five months of fixes.

## Specifics

| | |
|---|---|
| Cost | ~$0.35–0.55 per pipeline run · ~$0.05 per on-demand company check |
| Models | a capable model for judgement; a cheap model for extraction/classification; a web-search tool for top candidates and the agent |
| Coverage | ~22 predefined verticals plus any free-text industry on demand |
| Stack | Python on GitHub Actions; React + Vite + TypeScript + Vercel serverless; Google Sheets as the datastore |

## Reviewing it live

- **Public, no login:** the thesis and the engine at `bryanhanleyvc.com`, and the
  Second Layer Map at `bryanhanleyvc.com/map`.
- **Private (dealflow board + agent):** available on request — it holds working
  analysis and is deliberately gated.
- **The code:** both repos above; the git history is the build log.
