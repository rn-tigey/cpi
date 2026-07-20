# PCM Authoring Guide

The Product Context Model (PCM, `context/pcm.yaml`) is the only product-specific input to the
CPI pipeline and the single largest determinant of its signal quality. Every scan target, every
triage verdict, and every score is judged against this document. An afternoon spent writing it
well pays back every week the loop runs.

Start from `context/pcm.template.yaml` (`cpi init` seeds it for you), or draft it from your
existing PRDs and repo with `cpi draft-pcm` and then answer its open questions. Either way,
work through the six sections below. Bump `version` and log every material edit in
`context/pcm_changelog.md`.

## Ground rules

- **Be concrete.** "Enterprise auth" beats "security stuff". The LLM triages hundreds of signals
  against this text; vague entries produce vague triage.
- **Non-goals matter as much as goals** — they are what lets the filter say NO. Every explicit
  non-goal cheaply discards a whole class of noise.
- **Write for a reader with zero context.** The triage model knows nothing about your product
  except what this file says.

## The six sections

### 1. Capability map — what the product does *today*

Feature-cluster granularity, not a feature list. Each entry: a name, a one-sentence description
with real numbers where possible ("pulls customer data from 12 SaaS connectors nightly"), and
a maturity rating (`nascent | maturing | mature`). Maturity matters: a signal that threatens a
mature capability is defensive news; one that accelerates a nascent capability is opportunity.

### 2. User & job model — who it serves

Segments (sized: "mid-market ops teams, 50–500 employees"), jobs-to-be-done phrased as
outcomes ("detect revenue-impacting data problems before customers do"), and the top unmet
needs from research and support data. Unmet needs are strong triage fuel — signals that speak
to them get advanced.

### 3. Strategy frame — where you intend to win

- `where_we_win`: the few differentiators you actually bet on.
- `non_goals`: explicit and honest. "On-prem deployment", "becoming a BI tool". The filter
  discards toward these.
- `roadmap_themes`: current direction, so timing arguments can be judged.

### 4. Technical posture — what gates adoption

Stack in one line, hard dependencies (with their constraints — "Salesforce API, rate-limited"),
and organizational constraints ("two-engineer platform team; anything needing a new datastore
is expensive"). This section powers the Effort factor: the same idea scores differently for a
two-person team than for a platform org.

### 5. Competitive set — who else is moving

Direct, adjacent, and substitute competitors — substitutes especially ("spreadsheets + manual
checks" is often the real competitor). For each: `type` and an observed `direction` sentence.
Scanner hits on these names get classified as competitor activity.

### 6. Watch themes — what leadership declared interesting

5–10 named areas (the schema tolerates 1–12; fewer than 5 starves the scanners, more than 10
dilutes attention). Each theme carries:

- `name` — short and specific.
- `rationale` — why leadership cares, one sentence. This is read by the triage and scoring
  prompts.
- `arxiv_categories` — e.g. `["cs.LG", "cs.SE"]`; drives the arXiv scanner. Empty list is fine
  for non-research themes.
- `keywords` — 2–5 phrases; the scanners' fallback queries and cheap keyword hints.
  Use the phrases practitioners actually write, not internal jargon. In practice
  `cpi ground` translates each theme into per-channel vocabulary (`config/search.yaml`)
  that takes precedence over these — keywords still matter as the seed and fallback.

Good themes name a *development you'd act on*, not a topic: "embedded analytics
commoditization" (a move you'd respond to) beats "analytics" (a topic you'd drown in).

## Maintenance

The PCM is living: a light monthly review (named owner, calendar slot) plus updates whenever a
decision changes strategy — the Learn stage proposes these automatically (funded probe → watch
theme, killed idea → non-goal), and `cpi calibrate` drafts them for your confirmation. If triage
quality drifts, the fix is almost always here, not in the prompts.
