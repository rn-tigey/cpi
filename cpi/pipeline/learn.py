"""Stage 6 - Learn: quarterly calibration that closes the loop.

- Funded probes -> proposed PCM watch themes; kills -> proposed non-goals
- Score adjustments + spot-check reversals -> few-shot examples for prompts
- LLM-drafted calibration report incl. weight-adjustment proposals (human approves)
- Meta-question: what did we miss entirely, and which stage failed?
"""

from __future__ import annotations

import json
from datetime import date

from .. import llm, paths, store
from .. import pcm as pcm_mod


def _decisions_block() -> str:
    lines = []
    for d in store.iter_decisions():
        idea = store.get_idea(d.idea_id)
        title = idea.title if idea else d.idea_id
        lines.append(f"- {d.disposition.upper()}: {title} ({d.note or 'no note'})")
    return "\n".join(lines) or "(no decisions recorded yet)"


def _jsonl_block(name: str) -> str:
    rows = store.read_jsonl(paths.calibration_dir() / name)
    return "\n".join(f"- {json.dumps(r)}" for r in rows[-50:]) or "(none)"


PRUNE_MIN_TRIAGED = 10  # a source needs this many triaged signals before we judge it


def _scorecard_block() -> tuple[str, list[str]]:
    """Markdown table of per-source triage outcomes + prune candidates."""
    rows = store.source_scorecard()
    if not rows:
        return "(no triaged signals yet)", []
    lines = ["| source | advanced | parked | discarded | advance rate |",
             "|---|---|---|---|---|"]
    prune = []
    for r in rows:
        lines.append(f"| {r['source']} | {r['advance']} | {r['park']} | "
                     f"{r['discard']} | {r['advance_rate']:.0%} |")
        if r["total"] >= PRUNE_MIN_TRIAGED and r["advance"] == 0:
            prune.append(r["source"])
    if prune:
        lines.append("")
        lines.append(f"Prune candidates (>= {PRUNE_MIN_TRIAGED} triaged, zero advanced): "
                     + ", ".join(prune)
                     + " - consider removing them from sources.yaml or tightening their queries.")
    return "\n".join(lines), prune


def write_fewshots() -> int:
    """Compile human corrections into few-shot blocks injected into prompts."""
    n = 0
    reversals = store.read_jsonl(paths.calibration_dir() / "spot_checks.jsonl")
    reversed_only = [r for r in reversals if r.get("reversed")]
    if reversed_only:
        lines = ["Signals the triage agent wrongly discarded - do NOT discard signals like these:"]
        for r in reversed_only[-10:]:
            lines.append(f"- \"{r.get('title', r.get('signal_id'))}\" - human: {r.get('note', 'relevant')}")
        (paths.calibration_dir() / "fewshots_triage.md").write_text("\n".join(lines), encoding="utf-8")
        n += 1

    adjustments = store.read_jsonl(paths.calibration_dir() / "score_adjustments.jsonl")
    if adjustments:
        lines = ["Past human corrections to drafted scores - calibrate accordingly:"]
        for a in adjustments[-15:]:
            lines.append(f"- {a['factor']}: draft {a['draft']} -> human {a['final']} "
                         f"(idea {a['idea_id']}; draft reasoning was: {a.get('justification', '')[:120]})")
        (paths.calibration_dir() / "fewshots_score.md").write_text("\n".join(lines), encoding="utf-8")
        n += 1
    return n


def apply_decisions_to_pcm(auto_yes: bool = False) -> list[str]:
    """Funded -> watch-theme proposals; killed -> non-goal proposals."""
    import typer

    p = pcm_mod.load()
    changes = []
    theme_names = {t.name.lower() for t in p.watch_themes}
    non_goals = {g.lower() for g in p.strategy_frame.non_goals}

    for d in store.iter_decisions():
        idea = store.get_idea(d.idea_id)
        if not idea:
            continue
        if d.disposition == "fund" and idea.title.lower() not in theme_names:
            if auto_yes or typer.confirm(f"Add watch theme from funded probe: '{idea.title[:80]}'?", default=True):
                changes.append(f"watch theme added from funded probe {d.idea_id}: {idea.title}")
        elif d.disposition == "kill" and idea.title.lower() not in non_goals:
            if auto_yes or typer.confirm(f"Add non-goal from killed idea: '{idea.title[:80]}'?", default=True):
                changes.append(f"non-goal added from killed idea {d.idea_id}: {idea.title}")

    for c in changes:
        pcm_mod.append_changelog(c + " (edit pcm.yaml to finalize wording)")
    return changes


def run(missed: list[str] | None = None, auto_yes: bool = False) -> str:
    p = pcm_mod.load()
    block = pcm_mod.render_prompt_block(p)

    fewshots = write_fewshots()
    changes = apply_decisions_to_pcm(auto_yes=auto_yes)

    missed_block = "\n".join(f"- {m}" for m in (missed or [])) or "(none reported this quarter)"
    scorecard, _prune = _scorecard_block()
    report = llm.complete(
        "calibrate", pcm_block=block,
        decisions_block=_decisions_block(),
        adjustments_block=_jsonl_block("score_adjustments.jsonl"),
        reversals_block=_jsonl_block("spot_checks.jsonl"),
        missed_block=missed_block,
        scorecard_block=scorecard,
        weights_json=json.dumps(store.load_weights()),
    )

    out = paths.calibration_dir() / f"calibration-{date.today().strftime('%Y-%m')}.md"
    header = (f"# CPI Calibration — {date.today().isoformat()}\n\n"
              f"Few-shot files written: {fewshots} | PCM change proposals: {len(changes)}\n\n"
              f"## Source scorecard\n\n{scorecard}\n\n")
    out.write_text(header + report, encoding="utf-8")
    return str(out)
