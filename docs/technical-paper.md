# Continuous Product Intelligence — Technical Paper

**Technical Reference · Implementation · Reference implementation review, v0.1 · July 2026 · Ramana Nallajarla**

Companion to the [White Paper](white-paper.md), which defines the framework this
implementation realizes.

## 1 · System shape

Python 3.11 package, ~15 modules. Typer CLI, one command per stage. File-based store (JSON
per record, JSONL for append-only logs); no database, no service. Scheduling is cron / Task
Scheduler; the human-judgment commands (`spot-check`, `review-scores`, `brief`, `decide`,
`calibrate`) are deliberately unscheduled. All product specificity lives in `context/pcm.yaml` +
`config/sources.yaml`; re-targeting is `cpi init --dest` + `CPI_HOME`.

```
cpi/{cli,llm,models,pcm,store,paths}.py
cpi/scanners/{arxiv,rss,hn,funding,base}.py
cpi/pipeline/{triage,cluster,score,brief,learn}.py
context/pcm.yaml · config/{sources,weights}.yaml · prompts/*.md
data/** (gitignored) · briefs/ · tests/ (5 suites)
```

## 2 · Data model (pydantic)

| Model | Key fields / invariants |
|---|---|
| `SignalRecord` | `id = SHA-1(normalized URL)[:16]` — dedupe is structural, not best-effort. `source_class` enum: research \| industry \| competitor \| community \| funding. Summary + claimed_significance are LLM-written for long-form sources. |
| `TriageResult` | `disposition ∈ {advance, park, discard}` + rationale + confidence [0,1] + re_review_trigger (auto-defaulted for parks). Model name recorded per result. |
| `FactorScores` | 5 factors, int 1–5, effort pre-inverted. `weighted_total()` against config weights (defaults 30/25/20/15/10). Justification per factor required by schema. |
| `CandidateIdea` | `draft_scores` (LLM) and `final_scores` (human) kept separately; `effective_scores()` prefers final. `briefed_in` prevents re-briefing the same idea. |
| `Decision` | `idea_id` + fund \| park \| kill (validated) + note + timestamp. Append-only log. |
| `PCM` | Six sections; `watch_themes` validated 1–12 (5–10 recommended), each carrying arXiv categories + keywords that drive the scanners. Rendered once per run into a compact prompt block shared by every LLM call. |

## 3 · LLM layer

- **Single wrapper** (`llm.py`) — every call goes through it. Per-task model split:
  `claude-haiku-4-5` for volume tasks (summarize, triage), `claude-opus-4-8` with adaptive
  thinking for judgment tasks (score, brief, calibrate). Per-task `max_tokens`.
- **Structured outputs** — triage and scoring use schema-constrained JSON output, so
  dispositions and scores cannot come back malformed; no regex-parsing of free text.
- **Prompts are files** (`prompts/*.md`, `string.Template`) — editable without code changes.
  Calibration few-shots (`fewshots_<task>.md`, written by Stage 6) auto-inject when present.
- **Cost observability** — every call logs task, model, in/out tokens to `data/llm_usage.jsonl`;
  totals surface in `cpi status`.
- **`CPI_DRY_RUN=1`** — deterministic canned outputs for every task: keyless demo, offline
  tests, CI.

## 4 · Pipeline mechanics

| Stage | Implementation detail that matters |
|---|---|
| Scan | Four scanners behind a common base; idempotent via URL-hash ids; per-source rate limiting; `--no-llm` falls back to truncation instead of LLM summaries. Watch-theme arXiv categories/keywords come from the PCM, so scan targeting updates when the PCM does. |
| Triage | One schema-constrained call per signal against the PCM block. Parks get an explicit re-review trigger; `--rescore-parked` re-runs the parked queue monthly. Per-signal failures are counted, not fatal. |
| Cluster | TF-IDF + agglomerative clustering (cosine, distance threshold 0.8) over advanced-but-unclustered signals. No embeddings API dependency — cheap and local. The richest member signal names the idea. |
| Score | LLM drafts with per-factor justifications; `review-scores` is an interactive session where every human delta is appended to `score_adjustments.jsonl` — the calibration dataset is a side effect of normal use. |
| Brief | Hard cap 5 ideas; excess queues. Machine-enforced honesty: each page must contain all seven required sections, and the cons section must be ≥ 70% of the pros word count — one retry with the failure fed back, then hard-fail. `briefed_in` prevents duplicates across months. |
| Learn | Compiles spot-check reversals + score deltas into few-shot files; proposes PCM changes from decisions (funded → watch theme, killed → non-goal) with human confirmation; LLM-drafted calibration report reviews weights. Proposals land in the changelog, not silently in the PCM. |

## 5 · Testing & operations

Five pytest suites: PCM schema validation, normalization/dedupe, scoring math, brief validation
(section presence + pros/cons ratio), and an end-to-end pipeline dry-run. All network mocked;
LLM in dry-run — the suite runs keyless and offline. Cadences: scan+triage daily
(cron/schtasks examples shipped), RSS weekly, funding + parked-rescore + cluster + score
monthly; the judgment commands stay manual by design.

## 6 · Critical review — gaps against the design

The v0.1 implementation is faithful to the white paper's loop but ships with known deltas. In
priority order:

| Gap | Impact and suggested fix |
|---|---|
| No novelty score | The design's protection against discarding the genuinely new is absent — triage is relevance-only, so the filter's known bias toward the familiar is unmitigated. Fix: embed signals (any embeddings API or local model), flag low-max-similarity signals for human review. **Highest-priority gap.** |
| No parked-queue wake-ups | Parked signals only resurface at the monthly re-score; a new corroborating signal doesn't wake its parked relatives. Same embedding index fixes both this and novelty. |
| Triangulation gate not enforced | Nothing blocks a single-source-class idea from reaching a brief. Fix is small: assert ≥ 2 distinct `source_class` values across an idea's signals in `ranked_candidates()`; park otherwise. |
| TF-IDF clustering is brittle | Lexical clustering misses paraphrase-level relatedness (a paper and a changelog rarely share vocabulary) — exactly the cross-source clusters CPI cares most about. Acceptable at pilot volume; move to embeddings when the corpus grows. |
| No `cpi ask` | The interrogable evidence base (RAG over the signal corpus) is unimplemented. Depends on the same embedding index; sensible v0.2 scope. |
| Word-count cons check is a proxy | The ≥ 70% ratio enforces length, not argumentative force — an LLM can pad cons. Cheap improvement: a second-pass LLM critique scoring con specificity, with the ratio kept as a floor. |
| No retry/backoff on LLM calls | Transient API failures surface as per-signal errors. Fine interactively; add exponential backoff before scheduling unattended runs. |
| Init doesn't reset learned state | `cpi init` copies configs/prompts but does not explicitly exclude few-shot files if a home is copied wholesale; init must guarantee fresh calibration state for each adopting team. |

What the implementation gets right that the design under-specified: structural dedupe via
URL-hash ids; the draft/final score separation that makes calibration data a free by-product;
machine-enforced brief honesty with a feedback retry; per-call token accounting; and a dry-run
mode that makes the entire loop testable and demoable without keys.

**v0.2 scope in one line:** one embedding index unlocks the top three gaps (novelty, wake-ups,
better clustering) plus `cpi ask`.
