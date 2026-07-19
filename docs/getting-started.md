# Getting Started

This walks you from a fresh clone to your first Idea Brief. Budget: an hour to install and
configure, then the loop runs on a daily/weekly/monthly cadence. Concepts are defined in the
[White Paper](white-paper.md); implementation details in the [Technical Paper](technical-paper.md).

## 1. Install

```bash
git clone <repo-url> && cd cpi
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest   # sanity check — runs keyless and offline
```

Set your Anthropic key (or skip it and use dry-run mode to explore):

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: $env:ANTHROPIC_API_KEY = "sk-ant-..."
# or, keyless demo mode with canned LLM outputs:
export CPI_DRY_RUN=1
```

## 2. Create a home for your product

Everything product-specific — context, config, collected signals, briefs — lives in a *CPI home*
directory, separate from the code:

```bash
cpi init --dest ~/cpi-myproduct
export CPI_HOME=~/cpi-myproduct
```

`init` copies the PCM template, default source config, and prompt templates, and creates the
`data/` and `briefs/` layout. Keep this directory private — the PCM and briefs carry the same
confidentiality as your strategy documents.

## 3. Ground: author your PCM

Copy nothing, guess nothing — this is the step that determines signal quality.

1. Open `$CPI_HOME/context/pcm.yaml` (seeded from the template).
2. Fill in all six sections following the [PCM Authoring Guide](pcm-authoring.md). The
   watch themes' `arxiv_categories` and `keywords` directly drive the scanners.
3. Record the initial version in `$CPI_HOME/context/pcm_changelog.md`.
4. Edit `$CPI_HOME/config/sources.yaml`: replace the starter RSS/funding feeds with the
   analyst blogs, competitor changelogs, and funding feeds for *your* market.

## 4. Run the loop

```bash
# Daily (automate these — see README scheduling section)
cpi scan --source arxiv,hn      # collect + normalize signals
cpi triage                      # LLM: advance / park / discard vs. your PCM

# Weekly
cpi scan --source rss
cpi spot-check                  # human: sample 5 discards, keep the filter honest

# Monthly
cpi scan --source funding
cpi triage --rescore-parked     # parked signals get a second look
cpi cluster                     # group advanced signals into candidate ideas
cpi score                       # LLM drafts five-factor scores
cpi review-scores               # human: adjust scores (deltas become calibration data)
cpi brief                       # the ranked Idea Brief -> briefs/YYYY-MM-idea-brief.md
cpi decide <idea-id> fund       # record every disposition: fund | park | kill

# Quarterly
cpi calibrate                   # few-shots from your corrections; PCM/weight proposals
```

`cpi status` at any time shows counts per stage and LLM spend to date.

## 5. Read your first brief

After the first monthly pass, open `$CPI_HOME/briefs/<YYYY-MM>-idea-brief.md`. Each of the
top 3–5 ideas has a fixed page: the idea, the signal evidence, why now, cost of inaction, pros,
cons (enforced to be as substantial as the pros), the five-factor score, and a probe-sized next
step. Hold a 45-minute review, and record a fund/park/kill decision for every idea with
`cpi decide` — those decisions are what the Learn stage uses to make the next cycle better.

## Troubleshooting

- **`cpi scan` finds nothing** — check your PCM watch themes have concrete `keywords` and
  valid `arxiv_categories`, and that `sources.yaml` feeds resolve. HN ignores stories under
  `min_points`.
- **Triage advances too much/too little** — sharpen the PCM: non-goals discard, watch themes
  advance. Vague entries produce vague triage.
- **No API key handy** — `CPI_DRY_RUN=1` exercises every command with deterministic canned
  outputs; scanning still hits real feeds unless mocked.
- **Costs** — volume tasks run on a small model; a full monthly cycle at pilot volume
  (~50 signals) has cost well under $1 in API usage. Watch `cpi status` totals.
