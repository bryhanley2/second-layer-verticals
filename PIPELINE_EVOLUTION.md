# How the sourcing pipeline improved — an AI-assisted build

*Second Layer vertical pipeline · `github.com/bryhanley2/second-layer-verticals`*
*Prepared for Venture Institute — September 2026*

## The arc

I built the first version of this pipeline by hand between April and August 2026:
a script that pulled seed-stage companies from a few free sources, wrote them to a
Google Sheet on a schedule, and scored them. It worked, but it wasn't trustworthy —
it hallucinated company names, attached wrong websites, reported funding figures
that were guesses (one SEC lookup once summed a company's filings to **$5.5
billion**), let venture funds and accelerators through as if they were startups,
and — because of a single unset environment variable — every AI call was silently
failing while the sheet filled up with placeholder scores.

In early September I rebuilt it in a focused sprint using Claude Code as the
engineering surface: roughly **20 feature branches**, each one reviewed and merged
by me. Seven things changed.

## What changed

**1. Funding data you can cite.**
Multi-pass verification: Crunchbase → SEC Form D (most-recent filing only, sanity
caps, fund-entity filters) → the company's own website → a chunked Claude
cross-check. Every figure now carries a confidence level and a source link, or it
is stamped `UNVERIFIED`. A confirmation pass flags `CONFLICT`, `STAGE_MISMATCH`,
and `STALE`. A post-enrichment size re-check catches the "labelled seed, actually
raised $68M" cases that the first gate missed.

**2. Only real, on-thesis companies.**
A first-question gate — *"is this an operating, venture-backable company?"* —
rejects funds, accelerators, government programs, and research labs, and captures
the useful ones as future sourcing targets rather than discarding them.
Hallucinated and headline-shaped names are filtered at the source.

**3. A proprietary sourcing layer.**
Headless-browser scraping of specialist fund portfolios across 15 verticals, with
cheap-model extraction, a run-over-run diff so only genuinely new companies enter
the funnel, and a page-content-hash cache so unchanged pages cost nothing to
re-check.

**4. Scoring that ranks instead of gate-keeping.**
An anchored 9-factor rubric — explicit 1-to-10 definitions for each factor — fed
each company's own website text plus web-searched context for the top candidates,
then re-scored. The score became a sort key and a tier label, not a pass/fail, so
nothing promising is silently dropped.

**5. Cost and human control.**
The schedule was removed — the pipeline is manual-trigger-only now. Mechanical
work runs on a cheap model, judgement on a capable one, deep research on the top
three candidates only. A run went from unbounded cost to about **$0.35–0.55**.

**6. It fails loud.**
Every AI call is wrapped. A systemic failure — bad key, wrong model, rate
limiting — now stops the run and turns the workflow red, instead of producing a
sheet full of default scores that looks like a successful run.

**7. Memory.**
A watchlist tracks companies that aren't ready yet and re-checks them on every run
for movement — a new raise, hiring, fresh press — using free signals and
escalating to an AI call only when one fires. The point is to see a company
*before* its next round, not after.

## From engine to product

The pipeline now has a front end: **bryanhanleyvc.com** reads its output as a
ranked dealflow board and runs a live "check any company against the thesis"
agent — a standalone web application connected to an AI agent, doing a real
dealflow task.

## What this demonstrates

- **Using AI to build, not just to chat** — ~20 reviewed, merged feature branches
  in a short sprint, with feature-branch/PR discipline and explicit cost budgets.
- **Encoding investment judgement into software** — the thesis, the rubric, and
  the gates are all expressions of how I evaluate companies.
- **Knowing where AI needs guardrails** — every funding number is cited or
  flagged, the system fails closed rather than open, and a human still owns every
  investment decision.
