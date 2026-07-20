# Continuous Product Intelligence

*A closed-loop framework for turning industry, market, and research signals into ranked product decisions*

**White Paper · Product Strategy · Version 0.9 · July 2026 · Ramana Nallajarla**

> **Scope note.** This paper describes the CPI *framework* — the full design. The open-source
> reference implementation in this repository ships a subset of it: several design elements
> described below (novelty scoring, embedding-based parked-signal wake-ups, the triangulation
> gate, and the interrogable signal corpus of §10) are **not yet implemented**; the
> [Technical Paper](technical-paper.md) §6 tracks exactly which. Volume figures in this paper
> are design expectations, not measurements — the first pilots observed on the order of
> 50–150 signals per week, not the 200–500 projected in §5.

## 1 · Executive Summary

Every product organization is expected to stay current with industry trends, competitive moves,
and emerging research — yet in most organizations this work is ad hoc: it happens in browser
tabs, conference hallways, and quarterly panic cycles. Signals are found by accident, evaluated
by intuition, and lost when the person who spotted them moves on.

This paper proposes **Continuous Product Intelligence (CPI)**: a generic, product-agnostic
framework that (a) maintains a living model of the current product's context, (b) continuously
scans research venues, industry media, competitor activity, and community discussion, (c) filters
and scores incoming signals against that context, and (d) delivers a short, ranked list of product
ideas — each with explicit pros, cons, and evidence — on a predictable cadence. A feedback
stage tunes the system with every decision made.

CPI is operated as a hybrid: AI agents do the exhaustive collection and first-pass triage; product
leaders own judgment, scoring calibration, and the final recommendation. The framework can
be piloted by one product team in a single quarter and scaled organization-wide in two.

## 2 · The Problem: Ad Hoc Trend Discovery

Reviewing industry trends is a stated responsibility of nearly every product leader, but it is rarely
a designed process. Four failure modes recur:

- **Coverage is partial and biased.** Individuals scan the sources they already know. Research
  venues such as arXiv, standards bodies, and adjacent-industry activity are systematically
  under-watched relative to their influence.
- **Relevance is judged without shared context.** Whether a trend matters depends on the
  product's users, architecture, strategy, and constraints — context that lives in people's heads,
  not in a form a process (or an AI agent) can reason against.
- **Evaluation is unrepeatable.** Two leaders assessing the same signal reach different
  conclusions and cannot explain the difference. There is no rubric, so there is no learning.
- **Insight decays before it becomes action.** Findings surface in chat threads and slide
  appendices, disconnected from roadmap decisions. Six months later the same trend is
  "discovered" again.

The cost is asymmetric. Missing a genuine platform shift compounds into strategic debt: rushed
catch-up projects, lost differentiation, and eroded credibility with customers who noticed first. A
designed, continuous process is cheap insurance against an expensive class of failure.

## 3 · Framework Overview

CPI is a six-stage closed loop. The first stage builds the lens; the middle four move signals from
raw discovery to ranked recommendation; the last stage tunes the whole system with the
outcomes of real decisions.

| Stage | Name | Purpose |
|---|---|---|
| 1 | **Ground** | Build a living model of the product's context |
| 2 | **Scan** | Continuously collect signals from research, market, and community sources |
| 3 | **Filter** | Triage against the context model; discard noise quickly |
| 4 | **Assess** | Score surviving signals on impact, fit, effort, timing, confidence |
| 5 | **Recommend** | Deliver ranked idea briefs with pros, cons, and evidence |
| 6 | **Learn** | Feed decisions and outcomes back into the model and weights |

*Figure 1 — The six stages of the CPI loop. Learn feeds back into Ground, closing the cycle.*

Two design principles run through every stage. **Generic by construction**: the framework never
hard-codes a domain; all product specificity lives in the Stage 1 context model, so the same
pipeline serves any product by swapping that model. **Hybrid by default**: AI agents perform
exhaustive, tireless collection and first-pass reasoning; humans own the judgments that require
accountability — scoring calibration, kill decisions, and final recommendations.

## 4 · Stage 1: Ground — The Product Context Model

Relevance is meaningless without a reference point. Stage 1 produces the **Product Context
Model (PCM)** — a structured, versioned document that captures what the product is, who it
serves, and where it is going. It is the lens every later stage looks through, and the single largest
determinant of the framework's signal quality.

The PCM has six sections:

| Section | Contents |
|---|---|
| Capability map | What the product does today, at feature-cluster granularity, with maturity ratings |
| User & job model | Segments, jobs-to-be-done, and the top unmet needs from research and support data |
| Strategy frame | Where the product intends to win, explicit non-goals, and the current roadmap themes |
| Technical posture | Architecture, platform dependencies, and constraints that gate what is adoptable |
| Competitive set | Direct and adjacent competitors, plus substitutes, with their observed direction |
| Watch themes | 5–10 named areas leadership has declared strategically interesting, each with a rationale |

*Table 1 — Sections of the Product Context Model.*

The PCM is written once (a 2–3 week effort drawing on existing strategy docs, user research,
and architecture reviews) and then maintained: a light monthly review plus an update whenever
Stage 6 reports a decision that changes strategy or capability. Because the PCM is
machine-readable, it doubles as the system prompt context for the scanning and filtering agents.

## 5 · Stage 2: Scan — Multi-Source Signal Collection

Scanning is continuous, automated, and deliberately broad — the filter stage exists precisely so
the scan does not need to be conservative. Each source class has its own cadence and
collection method:

| Source class | Examples | Cadence |
|---|---|---|
| Academic research | arXiv categories mapped to watch themes; major conference proceedings; preprint servers in adjacent fields | Daily |
| Industry & analysts | Analyst reports, trade press, keynote announcements, standards-body drafts | Weekly |
| Competitor activity | Release notes, changelogs, pricing pages, job postings, patent filings | Weekly |
| Community discussion | Developer forums, Hacker News, Reddit, practitioner newsletters and podcasts | Daily |
| Capital flows | Funding rounds, M&A activity, and new-entrant launches in the competitive set | Monthly |

*Table 2 — Signal source classes, examples, and scanning cadences.*

Every collected item is normalized into a **signal record**: source, date, one-paragraph summary,
claimed significance, and links to raw material. Normalization is what makes heterogeneous
sources — a paper abstract, a changelog entry, a funding announcement — comparable
downstream. A typical scan yields 200–500 signal records per week for a single product;
volume is a feature at this stage, not a problem.

## 6 · Stage 3: Filter — Relevance Triage

Filtering reduces hundreds of weekly signals to the 10–20 worth human attention. An AI triage
agent evaluates each signal record against the PCM and assigns one of three dispositions:

- **Advance** — plausibly relevant to a watch theme, capability, or competitive position; moves to
  Stage 4 with a one-line rationale.
- **Park** — interesting but premature or tangential; stored with a re-review trigger (e.g., "revisit if
  a second independent implementation appears").
- **Discard** — no credible connection to the context model; logged for auditability, then dropped.

Relevance filtering has a known bias: it favors the familiar. A signal that maps cleanly onto an
existing watch theme scores well; a genuinely novel development — the kind that precedes
platform shifts — maps onto nothing and risks being discarded precisely because it is new. CPI
therefore adds a **novelty score** alongside the relevance disposition: signals that are
semantically distant from everything previously seen are flagged for human review even when
their relevance is unclear. Relevance finds what we know to look for; novelty protects against
what we don't.

The parked queue is also smarter than a monthly re-read. Every signal is stored with a semantic
embedding, so when a new signal arrives, related parked signals wake up automatically: a
parked paper from March resurfaces the day a competitor ships something similar in June.
Accumulating wake-ups on the same theme are themselves a signal — evidence that a trend is
gathering mass.

Two safeguards keep the filter honest. First, a weekly human **spot-check** samples the discard
pile; if genuinely relevant signals are being dropped, the triage prompt or the PCM watch
themes are corrected. Second, the parked queue is **re-scored monthly**, because relevance
changes as the context model evolves — yesterday's tangent can be tomorrow's theme.

## 7 · Stage 4: Assess — Scoring What Survives

Advanced signals receive a structured assessment. Related signals are first clustered into
**candidate ideas** (three papers, a competitor launch, and a funding round often describe one
underlying trend). Each candidate idea is then scored on five factors, 1–5 each:

| Factor | Question it answers | Weight |
|---|---|---|
| Impact | If this works, how much does it move user value or business outcomes? | 30% |
| Strategic fit | Does it strengthen where we intend to win, or pull us off-strategy? | 25% |
| Effort | What does adoption cost given our technical posture? (inverted: lower effort scores higher) | 20% |
| Timing | Is the window open now — mature enough to adopt, early enough to differentiate? | 15% |
| Confidence | How strong and independent is the evidence behind the signal cluster? | 10% |

*Table 3 — The five-factor relevance score. Weights are defaults; Stage 6 tunes them per organization.*

The AI agent drafts scores with written justifications; a product leader reviews and adjusts
them. Disagreements between drafted and adjusted scores are recorded — they are the
calibration data Stage 6 uses to improve the drafts. The output of Stage 4 is a scored,
deduplicated shortlist, typically 5–8 candidate ideas per monthly cycle.

A structural rule strengthens the Confidence factor: **triangulation**. A candidate idea must be
supported by signals from at least two independent source classes — research plus capital,
community plus competitor activity — before it can reach a brief. A single-source idea, however
exciting, stays in the parked queue until a second class corroborates it. This one rule cheaply
eliminates most hype-driven false positives, since hype tends to concentrate in a single channel
before it spreads.

## 8 · Stage 5: Recommend — The Ranked Idea Brief

The framework's deliverable is the **Idea Brief**: a monthly document presenting the top 3–5
candidate ideas in rank order. Each idea occupies one page with a fixed structure:

| | |
|---|---|
| **The idea** — one sentence, in product terms | **Score** — five factors, weighted total, rank |
| **The signal** — what was observed, with sources | **Pros** — 3–4, each tied to a scoring factor |
| **Why now** — the timing argument | **Cons & risks** — 3–4, stated as plainly as the pros |
| **Cost of inaction** — what happens if we pass | **Suggested next step** — smallest probe that reduces uncertainty |

*Figure 2 — Fixed structure of each idea page in the monthly brief.*

Two rules protect the brief's credibility. **Cons are mandatory and symmetrical**: an idea with four
pros and one token con is returned for rework. Every recommendation names a next step that
is a **probe, not a project** — a spike, a customer conversation set, a competitive teardown — so
leadership is deciding to spend days, not quarters. Recommendations are reviewed in a standing
45-minute monthly session; each idea receives an explicit disposition: **fund the probe, park,
or kill**.

## 9 · Stage 6: Learn — Closing the Loop

Most trend processes die because they never learn. Stage 6 makes learning structural. Three
feedback paths run continuously:

- **Decisions update the context model.** A funded probe becomes a watch theme; a killed idea
  becomes an explicit non-goal, preventing its re-litigation.
- **Outcomes recalibrate the scores.** Every quarter, past briefs are re-read against what
  actually happened. Systematic misses (e.g., timing consistently scored too optimistically)
  adjust factor weights and agent prompts.
- **Human corrections train the triage.** Spot-check reversals and score adjustments
  accumulate into examples that sharpen the AI's first-pass judgment.

The quarterly retrospective also asks the meta-question: *what did we miss entirely?* Any
significant industry development that never appeared in a brief is traced back — was it never
scanned, wrongly discarded, or under-scored? — and the responsible stage is fixed.

## 10 · Operating Model

CPI is intentionally light on headcount. For a single product, steady-state operation requires
roughly half a day per week of product-leader time plus AI agent infrastructure:

| Role | Owns | Time |
|---|---|---|
| AI agents | Scanning, normalization, triage drafts, score drafts, brief drafting | Continuous |
| Framework owner (product manager / product leader) | PCM maintenance, spot-checks, score review, brief finalization | ~4 hrs / week |
| Domain reviewers | Deep assessment of ideas touching their area (eng, design, research) | ~2 hrs / month each |
| Leadership panel | Monthly brief review; probe/park/kill dispositions; weight approval | 45 min / month |

*Table 4 — Roles and steady-state time commitment for one product.*

Cadences nest cleanly: scanning runs daily, triage weekly, briefs monthly, calibration quarterly.
Nothing in the loop waits on an annual planning cycle — which is the point.

Because every signal is stored with its embedding, the corpus doubles as an interrogable
evidence base: leadership can ask ad-hoc questions ("what have we seen on agent
interoperability in the last quarter?") and get grounded answers with sources between briefs,
rather than waiting for the monthly cycle. The same corpus can be exposed as a
machine-readable feed so other internal tools and agents consume CPI's signals directly.

## 11 · Implementation Roadmap

CPI reaches full operation in three phases across two quarters:

| Phase | Work | Exit criterion |
|---|---|---|
| 1 · Foundation (Weeks 1–4) | Write the PCM for one pilot product; select and configure sources; stand up scanning and normalization agents | Signals flowing from all five source classes into normalized records |
| 2 · Pilot loop (Weeks 5–12) | Run the full loop monthly: triage, scoring, two idea briefs delivered and reviewed; tune prompts and weights from spot-checks | Leadership panel funds, parks, or kills every idea in two consecutive briefs |
| 3 · Scale (Weeks 13–24) | Onboard remaining products (new PCM each, shared pipeline); first quarterly calibration; publish the playbook | Every product line receiving a monthly brief; calibration retro completed |

*Table 5 — Three-phase rollout across two quarters.*

## 12 · Risks and Mitigations

- **Signal flooding.** If briefs balloon past five ideas, discipline erodes. *Mitigation:* the brief is
  capped by rule; excess ideas queue for the next cycle.
- **Context model drift.** A stale PCM silently degrades every downstream stage. *Mitigation:*
  monthly review is a named owner's calendar obligation; Stage 6 updates are automatic triggers.
- **AI over-trust.** Drafted scores accepted without review become the de facto decision.
  *Mitigation:* mandatory human sign-off on every published score; disagreement rate is itself a
  tracked metric — a rate near zero is a red flag.
- **Novelty theater.** The process rewards finding shiny things rather than useful ones.
  *Mitigation:* the quarterly retro scores the process on decisions influenced, not signals collected.
- **Confidentiality.** Scanned material and the PCM concentrate competitive insight. *Mitigation:*
  the PCM and briefs carry the same access controls as strategy documents.

## 13 · Prior Art and Differentiation

CPI does not exist in a vacuum. Three adjacent categories each solve a slice of the problem:

- **Commercial competitive-intelligence platforms** (Quid, Contify, Crayon, AlphaSense)
  aggregate vast source coverage with AI summarization, but are competitor-centric, priced
  for large enterprises (typically $50K+/year), and stop at insight delivery — they do not ground
  findings in a product context model or produce decision-ready recommendations with pros
  and cons.
- **Open-source horizon-scanning tools** — Nesta's Innovation Sweet Spots (triangulating
  research funding, venture investment, and news discourse), domain-agnostic scanning
  pipelines with embedding search and human moderation, and lightweight trend aggregators
  — prove the scanning and enrichment layers are buildable with modest effort, but none score
  against a specific product's strategy or close a learning loop.
- **Foresight methodology from institutional practice** (weak-signal detection, PESTLE framing,
  scenario planning) supplies rigor but is typically run as a periodic consulting exercise, not a
  continuous system.

CPI's differentiation is the combination: a product context model as the relevance lens,
weighted scoring with triangulation, briefs that argue both sides, and a learning loop that
tunes the system from real decisions. Several design choices above — novelty scoring,
embedding-based wake-ups, cross-source triangulation — are deliberately borrowed from the
strongest prior art and integrated into one closed loop.

The same separation makes CPI a candidate for open-sourcing: the pipeline contains no
proprietary logic, and all product specificity lives in two configuration files (the PCM and the
source list), which remain private with strategy-document confidentiality. One nuance matters:
while the pipeline is generic, the learned state — calibration logs, tuned weights, prompt
examples accumulated by Stage 6 — is product-specific and must start fresh for each adopting
team. The differentiated value in sharing it is the operating discipline itself: the
context-model-as-lens, the calibration logging, and the fund/park/kill cadence, documented so
another team can run the loop, not just the code.

## 14 · Conclusion

Trend awareness is already every product leader's job; CPI simply gives that job a design. By
separating context (Stage 1) from collection (Stage 2) from judgment (Stages 3–5), the
framework stays generic across products while producing recommendations that are specific,
evidenced, and honestly argued on both sides. The hybrid operating model keeps the cost
at hours per week, and the learning stage means the system is better every quarter than the
one before.

The recommended next step is itself a probe: fund the four-week Foundation phase for one pilot
product, and judge the framework by its first two idea briefs.
