# CPI — Continuous Product Intelligence

A closed-loop system that maintains a context model of a product, continuously scans external
sources (arXiv, RSS, Hacker News, funding news), LLM-triages and scores incoming signals
against that context, and produces a monthly ranked **Idea Brief** — the top 3–5 product ideas,
each with pros, cons, evidence, and a probe-sized next step.

**Generic by construction** — no domain logic in code. All product specificity lives in
`context/pcm.yaml` (the Product Context Model) and `config/sources.yaml`. Swap those two
files (or use `cpi init`) and the pipeline re-targets to a different product.

**Hybrid by default** — AI agents do the exhaustive collection and first-pass triage; humans own
scoring calibration, kill decisions, and the final recommendation.

Read more: [White Paper](docs/white-paper.md) (the framework) ·
[Technical Paper](docs/technical-paper.md) (this implementation) ·
[Getting Started](docs/getting-started.md) · [PCM Authoring Guide](docs/pcm-authoring.md)

## Setup

Install from source (a wheel install would not carry the `context/`, `config/`, and `prompts/`
template folders that `cpi init` copies — packaging them via `importlib.resources` is future work):

```bash
git clone https://github.com/rn-tigey/cpi.git && cd cpi
pip install -e ".[dev]"

# LLM access:
#   export ANTHROPIC_API_KEY=sk-ant-...        (Windows: $env:ANTHROPIC_API_KEY = "sk-ant-...")
# Keyless / offline demo:
#   export CPI_DRY_RUN=1                        (deterministic canned LLM outputs)
```

Models used: `claude-haiku-4-5` for volume tasks (summaries, triage), `claude-opus-4-8` for
judgment tasks (scoring, briefs, calibration). The per-task model map lives in `cpi/llm.py` —
edit it there to use different models. All calls go through that one wrapper; token usage is
logged to `data/llm_usage.jsonl` (see totals in `cpi status`).

## The six stages → commands

| Stage | What happens | Command | Cadence |
|---|---|---|---|
| 1 Ground | Maintain the PCM (the lens) | edit `context/pcm.yaml` + changelog | monthly review |
| 2 Scan | Collect + normalize signals | `cpi scan --source arxiv,hn` / `...rss,funding` | daily / weekly / monthly |
| 3 Filter | LLM triage: advance/park/discard | `cpi triage` (+ `--rescore-parked` monthly) | daily-weekly |
| 3b Audit | Human spot-check of discards | `cpi spot-check` | weekly |
| 4 Assess | Cluster → draft scores → human review | `cpi cluster && cpi score && cpi review-scores` | monthly |
| 5 Recommend | Ranked Idea Brief (top ≤5) | `cpi brief` then `cpi decide <id> fund\|park\|kill` | monthly |
| 6 Learn | Calibration: few-shots, PCM & weight proposals | `cpi calibrate [--missed "..."]` | quarterly |

`cpi status` shows counts per stage at any time.

## Quickstart

```bash
# 1. Create a working home for your product
cpi init --dest ~/cpi-myproduct
export CPI_HOME=~/cpi-myproduct        # Windows: $env:CPI_HOME = "..."

# 2. Ground: author your PCM (see docs/pcm-authoring.md)
#    edit $CPI_HOME/context/pcm.yaml and $CPI_HOME/config/sources.yaml

# 3. Run the loop
cpi scan --source arxiv,hn
cpi triage
cpi status
```

## Scheduling

**cron:**
```cron
0 7 * * *   CPI_HOME=/path/to/home cpi scan --source arxiv,hn && cpi triage
0 8 * * 0   CPI_HOME=/path/to/home cpi scan --source rss
0 8 1 * *   CPI_HOME=/path/to/home cpi scan --source funding && cpi triage --rescore-parked && cpi cluster && cpi score
```

**Windows (Task Scheduler):**
```powershell
schtasks /Create /TN "CPI daily scan"    /SC DAILY  /ST 07:00 /TR "cmd /c set CPI_HOME=C:\path\to\home&& cpi scan --source arxiv,hn && cpi triage"
schtasks /Create /TN "CPI weekly rollup" /SC WEEKLY /D SUN /ST 08:00 /TR "cmd /c set CPI_HOME=C:\path\to\home&& cpi scan --source rss"
schtasks /Create /TN "CPI monthly"       /SC MONTHLY /D 1  /ST 08:00 /TR "cmd /c set CPI_HOME=C:\path\to\home&& cpi scan --source funding && cpi triage --rescore-parked && cpi cluster && cpi score"
```

Spot-checks, `review-scores`, `brief`, `decide`, and `calibrate` are deliberately **manual** —
they are the human half of the hybrid.

## First eight weeks (runbook)

1. **Week 1 — Ground.** Author `context/pcm.yaml` from the template. Get the non-goals and
   watch themes right — they are the filter's teeth. Log edits in `context/pcm_changelog.md`.
   Configure `config/sources.yaml` feeds for your market.
2. **Weeks 1–4 — Scan + triage daily.** `cpi scan --source arxiv,hn && cpi triage`. Expect
   dozens-to-hundreds of signals/week; triage should advance only 10–20.
3. **Weekly — keep the filter honest.** `cpi spot-check` (5 discards, ~10 minutes). Reversals
   are logged automatically and sharpen the triage prompt at calibration.
4. **Week 4 — first assess pass.** `cpi cluster && cpi score && cpi review-scores`. Adjust
   scores freely — your deltas are the calibration data.
5. **Week 8 — first brief.** `cpi brief`, hold the 45-minute review, record every disposition
   with `cpi decide`. Two briefs in, run the first `cpi calibrate`.

## Layout

```
cpi/               the Python package (cli, llm, models, pcm, store, scanners/, pipeline/)
context/           pcm.template.yaml (copy to pcm.yaml), pcm_changelog.md
config/            sources.yaml, weights.yaml
prompts/           editable LLM prompt templates (no code changes needed)
data/              signals/, triage/, discards/, ideas/, calibration/, decisions/  (gitignored)
briefs/            YYYY-MM-idea-brief.md
tests/             pytest suite (network mocked, LLM dry-run)
docs/              white paper, technical paper, guides
```

## Tests

Keyless and offline — `tests/conftest.py` forces `CPI_DRY_RUN=1`:

```bash
pytest
```

## License

MIT — see [LICENSE](LICENSE).
