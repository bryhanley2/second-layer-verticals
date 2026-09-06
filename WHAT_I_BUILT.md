# What I built — an AI-run seed-stage sourcing engine

*Second Layer sourcing · `bryanhanleyvc.com` · pipeline in `second-layer-verticals`, web app in `venture-capital`*
*Prepared for Venture Institute — September 2026*

## One paragraph

I built an AI-run sourcing engine for a seed-stage investment thesis I call the
Second Layer Approach: back the companies solving the problems a dominant trend
creates, not the companies that *are* the trend. The system has two parts. A
pipeline — running on demand, never on a schedule — sources seed-stage companies
from specialist fund portfolios, SEC filings, accelerator cohorts, and sector
press; verifies each company's funding against citable sources or marks it
unverified; filters out anything that fails the thesis or isn't a real operating
company; and scores the survivors against a nine-factor rubric. A web application
at bryanhanleyvc.com is the cockpit on top of it: a public "Second Layer Map"
that lays out a trend's derived problem layers and the vetted companies attacking
each, a private ranked dealflow board, a watchlist that re-checks
promising-but-not-yet companies for movement between runs, and a live agent that
assesses any company you name against the thesis. Every funding figure is cited
or flagged, the pipeline fails loudly rather than writing quiet guesses, and no
investment decision is automated — the machine proposes, a human decides.

## The thesis

The Second Layer Approach: the largest returns often go not to the companies
riding a dominant trend but to the ones solving the problems that trend creates.
As AI scales faster than most industries can absorb it, the operational,
knowledge, and compliance gaps it opens are where under-priced opportunity sits.

## The engine

A manual-trigger pipeline (GitHub Actions, no cron) that, for any given vertical
or free-text industry:

- **Sources** from free and proprietary channels — a YC company dataset, SEC
  EDGAR Form D filings, sector RSS, targeted AI research, YC Launch posts,
  Product Hunt, VC newsletters, and a headless-browser scrape of specialist fund
  portfolios and government program pages across fifteen verticals, diffed run
  over run so only genuinely new companies enter.
- **Verifies funding** through a multi-pass check — Crunchbase, then the
  company's own SEC Form D, then its website, then a cross-check by the model.
  Every figure carries a source and a confidence level, or it is stamped
  unverified. A confirmation pass flags conflicts, stage mismatches, and stale
  figures.
- **Filters** — rejects funds, accelerators, and government programs; drops
  companies that *are* the trend rather than a second-layer response to it;
  captures the good non-companies as future sourcing targets.
- **Scores** — a nine-factor rubric with explicit anchors, fed each company's own
  website text and web-searched context for the top candidates, then re-scored.
  The score ranks; it doesn't gate.
- **Remembers** — companies that clear the thesis but aren't ready are added to a
  watchlist and re-checked every run for movement (a new raise, hiring, fresh
  press) using free signals, escalating to a single AI call only when a signal
  fires.

## The cockpit

A React web application:

- **Second Layer Map** (public) — one trend, its derived problem layers, and a
  curated set of vetted seed-stage companies at each, auto-maintained by the
  pipeline and gated to companies above a real score with a manual override.
- **Dealflow board** (private, request-access) — the full ranked list with
  second-layer logic, verified funding, strengths, and risks.
- **Company-check agent** (private) — enter any company, get a live web-searched
  read on whether it's Second Layer, its real stage, its founders, and its
  funding, with sources.

## The discipline

Funding is cited or flagged, never guessed. Founders are marked "needs manual
lookup" rather than fabricated. The pipeline turns its workflow red on a systemic
failure instead of writing default scores. The public map only shows what cleared
the score bar and a human review. No investment call is automated.

## Built with AI

The entire system was built using AI as the engineering surface — not a chat
assistant, but the tool that wrote and revised the code across roughly twenty
reviewed feature branches. It is a demonstration of how AI changes what one
person can source, verify, and cover in venture.

## Specifics

| | |
|---|---|
| Cost | ~$0.35–0.55 per pipeline run · ~$0.05 per on-demand company check · ~$0.01 per map rebuild |
| Models | a capable model for judgement (scoring, thesis evaluation, funding verification); a cheap model for mechanical extraction and classification; a live web-search tool for top candidates and the interactive agent |
| Coverage | ~22 predefined verticals plus any free-text industry on demand |
| Datastore | Google Sheets — the pipeline writes, the web app reads via a read-only service account |
| Stack | Python pipeline on GitHub Actions; React + Vite + TypeScript frontend and serverless functions on Vercel; custom domain |
| Sourcing | ~7 free feeds/APIs plus a proprietary scrape layer over specialist fund portfolios and federal program pages |
| Guardrails | multi-source funding verification, non-company rejection, fail-closed scoring, unverified-founder marking, curated public surface |
