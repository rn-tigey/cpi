# Getting Started

This walks you from a fresh clone to your first Idea Brief. Budget: an hour to install and
configure, then the loop runs on a daily/weekly/monthly cadence. Concepts are defined in the
[White Paper](white-paper.md); implementation details in the [Technical Paper](technical-paper.md).

## 1. Install

```bash
git clone https://github.com/rn-tigey/cpi.git && cd cpi
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

**Shortcut if you already have artifacts:** point CPI at your PRDs, strategy docs, or the
product's git repo and let it draft the PCM for you:

```bash
cpi draft-pcm --docs ./my-prds --repo ./my-product-repo
```

The machine extracts what documents state well (capabilities, stack, roadmap); what they
never state — non-goals, where you truly win — comes back as `OPEN QUESTION` comments in
the draft that you must answer yourself. Review every entry, bump `version` to `"1"`, and
continue with steps 3–5 below. Otherwise, author it by hand:

1. Open `$CPI_HOME/context/pcm.yaml` (seeded from the template).
2. Fill in all six sections following the [PCM Authoring Guide](pcm-authoring.md). The
   watch themes' `arxiv_categories` and `keywords` directly drive the scanners.
3. Record the initial version in `$CPI_HOME/context/pcm_changelog.md`.
4. Edit `$CPI_HOME/config/sources.yaml`: replace the starter RSS/funding feeds with the
   analyst blogs, competitor changelogs, and funding feeds for *your* market.
5. Generate the search criteria:

   ```bash
   cpi ground     # writes $CPI_HOME/config/search.yaml
   ```

   This translates each watch theme into the vocabulary each channel actually uses (academic
   phrasing for arXiv, developer phrasing for HN, product-category phrasing for press) and adds
   a standard set built from your competitor names. Review and edit the file — it is config,
   not magic. Without it, scanners fall back to your raw PCM keywords, which are usually too
   academic to match headlines. Re-run with `--force` after significant PCM edits.

## 4. Your first brief — one command, one sitting

You do not need any schedule or routine to try CPI. One command runs the whole automated
half — scan → triage → cluster → score → brief:

```bash
cpi run
```

Ten minutes later (mostly feed-fetching), open `$CPI_HOME/briefs/<YYYY-MM>-idea-brief.md`.
Each ranked idea has a fixed page: the idea, the signal evidence, why now, cost of inaction,
pros, cons (a validation rule requires them to match the pros in length — real substance is on
the reviewer), the five-factor score, and a probe-sized next step. If the first run finds too
few signals to make ideas, run it again in a few days — signals accumulate.

Judge CPI by this brief: if nothing in it is worth a second look for your product, sharpen the
PCM (usually the watch themes and non-goals) and try again before investing anything more.

`cpi status` at any time shows counts per stage, per-source health, and LLM spend to date.

## 5. Operating it properly — once it's earned it

When the briefs prove useful, graduate from one-shot runs to the operating rhythm. This is
where CPI stops being a report generator and becomes a loop: the human steps below are what
make each cycle better than the last.

```bash
# Daily (automate these — see README scheduling section)
cpi scan --source arxiv,hn      # collect + normalize signals
cpi triage                      # LLM: advance / park / discard vs. your PCM

# Weekly
cpi scan --source crossref,rss
cpi spot-check                  # human: sample 5 discards, keep the filter honest

# Monthly
cpi scan --source funding
cpi triage --rescore-parked     # parked signals get a second look
cpi cluster && cpi score        # group into ideas, draft five-factor scores
cpi review-scores               # human: adjust scores (deltas become calibration data)
cpi brief                       # the ranked Idea Brief -> briefs/YYYY-MM-idea-brief.md
cpi decide <idea-id> fund       # record every disposition: fund | park | kill

# Quarterly
cpi calibrate                   # few-shots from your corrections; PCM/weight proposals
```

Skipping the human steps costs you nothing today and everything later: without spot-checks
nobody audits the filter, without score reviews and decisions the Learn stage has no data,
and the system stays exactly as good as it was on day one. Hold the monthly review as a
45-minute session and record a fund/park/kill decision for every briefed idea.

## Troubleshooting

- **`cpi scan` finds nothing** — run `cpi ground` if you haven't (raw PCM keywords rarely
  match channel vocabulary), check watch themes have valid `arxiv_categories`, and confirm
  `sources.yaml` feeds resolve. HN ignores stories under `min_points`. arXiv's
  `lookback_days` must cover the gap since your last scan — 7 days of lookback on a monthly
  cadence misses three weeks of papers.
- **Triage advances too much/too little** — sharpen the PCM: non-goals discard, watch themes
  advance. Vague entries produce vague triage.
- **No API key handy** — `CPI_DRY_RUN=1` exercises every command with deterministic canned
  outputs; scanning still hits real feeds unless mocked.
- **Costs** — volume tasks run on a small model; a full monthly cycle at pilot volume
  (~50 signals) has cost well under $1 in API usage. Watch `cpi status` totals.
