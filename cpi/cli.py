"""CPI command-line interface. One command per stage of the loop."""

from __future__ import annotations

import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from . import paths, store
from . import pcm as pcm_mod

app = typer.Typer(help="Continuous Product Intelligence - scan, triage, score, brief, learn.",
                  no_args_is_help=True)


@app.command()
def init(dest: Path = typer.Option(..., help="Folder to initialize for a new product")):
    """Bootstrap a new CPI home (PCM template + configs + prompts) for another product."""
    src = paths.home()
    dest.mkdir(parents=True, exist_ok=True)
    for sub in ("config", "prompts"):
        shutil.copytree(src / sub, dest / sub, dirs_exist_ok=True)
    (dest / "context").mkdir(exist_ok=True)
    shutil.copy(src / "context" / "pcm.template.yaml", dest / "context" / "pcm.template.yaml")
    target_pcm = dest / "context" / "pcm.yaml"
    if not target_pcm.exists():
        shutil.copy(src / "context" / "pcm.template.yaml", target_pcm)
    (dest / "context" / "pcm_changelog.md").write_text("# PCM Changelog\n", encoding="utf-8")
    for d in ("data", "briefs"):
        (dest / d).mkdir(exist_ok=True)
    typer.echo(f"Initialized CPI home at {dest}")
    typer.echo(f"1) Edit {target_pcm} for the new product")
    typer.echo(f"2) Run with: set CPI_HOME={dest} (or export CPI_HOME={dest})")


@app.command()
def scan(source: str = typer.Option("arxiv,rss,hn", help="Comma-separated: arxiv,rss,hn,funding"),
         no_llm: bool = typer.Option(False, help="Skip LLM summaries (truncate instead)")):
    """Stage 2 - collect signals from the configured sources."""
    from .scanners import SCANNERS

    paths.ensure_layout()
    p = pcm_mod.load()
    config = store.load_sources()
    total = 0
    for name in [s.strip() for s in source.split(",") if s.strip()]:
        if name not in SCANNERS:
            typer.echo(f"Unknown source '{name}' (valid: {', '.join(SCANNERS)})")
            raise typer.Exit(1)
        typer.echo(f"[scan] {name} ...")
        records = SCANNERS[name].scan(p, config, use_llm=not no_llm)
        typer.echo(f"[scan] {name}: {len(records)} new signal(s)")
        total += len(records)
    typer.echo(f"Done - {total} new signal(s) collected.")


@app.command()
def triage(limit: Optional[int] = typer.Option(None, help="Max signals this run"),
           rescore_parked: bool = typer.Option(False, help="Re-score the parked queue (monthly)")):
    """Stage 3 - LLM triage of new signals against the PCM."""
    from .pipeline import triage as triage_mod

    paths.ensure_layout()
    counts = triage_mod.run(limit=limit, rescore_parked=rescore_parked)
    typer.echo(f"Triage: {counts}")


@app.command("spot-check")
def spot_check(n: int = typer.Option(5, help="Sample size from the discard pile")):
    """Weekly human audit of discards; reversals become calibration data."""
    discards = store.signals_by_disposition("discard")
    if not discards:
        typer.echo("Discard pile is empty.")
        raise typer.Exit()
    sample = random.sample(discards, min(n, len(discards)))
    reversed_count = 0
    for s in sample:
        t = store.get_triage(s.id)
        typer.echo(f"\n[{s.source_name}] {s.title}\n  {s.summary[:250]}\n  {s.url}")
        typer.echo(f"  discarded because: {t.rationale if t else '?'}")
        if typer.confirm("  Was this discard WRONG (signal actually relevant)?", default=False):
            note = typer.prompt("  Why is it relevant", default="")
            store.append_jsonl(paths.calibration_dir() / "spot_checks.jsonl", {
                "signal_id": s.id, "title": s.title, "reversed": True, "note": note,
            })
            reversed_count += 1
        else:
            store.append_jsonl(paths.calibration_dir() / "spot_checks.jsonl", {
                "signal_id": s.id, "title": s.title, "reversed": False,
            })
    typer.echo(f"\nSpot-check done: {reversed_count}/{len(sample)} reversal(s) logged.")
    if reversed_count:
        typer.echo("Reversals feed the triage prompt at the next `cpi calibrate`.")


@app.command()
def cluster():
    """Stage 4a - group advanced signals into candidate ideas."""
    from .pipeline import cluster as cluster_mod

    ideas = cluster_mod.run()
    typer.echo(f"{len(ideas)} new candidate idea(s).")


@app.command()
def score(rescore: bool = typer.Option(False, help="Re-draft existing scores")):
    """Stage 4b - LLM drafts factor scores for unscored ideas."""
    from .pipeline import score as score_mod

    n = score_mod.run(rescore=rescore)
    typer.echo(f"Scored {n} idea(s). Review with: cpi review-scores")


@app.command("review-scores")
def review_scores():
    """Human accepts/adjusts drafted scores; deltas are logged for calibration."""
    from .pipeline import score as score_mod

    n = score_mod.review_interactive()
    typer.echo(f"Reviewed {n} idea(s).")


@app.command()
def brief(month: Optional[str] = typer.Option(None, help="YYYY-MM (default: current)")):
    """Stage 5 - render the monthly ranked Idea Brief (top 5 max)."""
    from .pipeline import brief as brief_mod

    path = brief_mod.run(month=month)
    typer.echo(f"Brief written: {path}")


@app.command()
def decide(idea_id: str = typer.Argument(...),
           disposition: str = typer.Argument(..., help="fund | park | kill"),
           note: str = typer.Option("", help="Leadership note")):
    """Record a leadership disposition for a briefed idea."""
    from .models import Decision

    if store.get_idea(idea_id) is None:
        typer.echo(f"Unknown idea id: {idea_id}")
        raise typer.Exit(1)
    store.append_decision(Decision(idea_id=idea_id, disposition=disposition, note=note,
                                   decided_at=datetime.now(timezone.utc)))
    typer.echo(f"Recorded: {idea_id} -> {disposition}")


@app.command()
def calibrate(missed: list[str] = typer.Option([], help="Developments we missed entirely (repeatable)"),
              yes: bool = typer.Option(False, "--yes", help="Auto-accept PCM change proposals")):
    """Stage 6 - quarterly calibration: few-shots, PCM proposals, weight review."""
    from .pipeline import learn as learn_mod

    path = learn_mod.run(missed=list(missed), auto_yes=yes)
    typer.echo(f"Calibration report: {path}")


@app.command()
def status():
    """Counts per pipeline stage."""
    paths.ensure_layout()
    signals = list(store.iter_signals())
    triaged = list(store.iter_triage())
    by_disp = {"advance": 0, "park": 0, "discard": 0}
    for t in triaged:
        by_disp[t.disposition.value] += 1
    ideas = list(store.iter_ideas())
    scored = [i for i in ideas if i.effective_scores()]
    briefed = [i for i in ideas if i.briefed_in]
    decisions = store.iter_decisions()

    typer.echo(f"PCM:        {pcm_mod.load().product_name} (v{pcm_mod.load().version})")
    typer.echo(f"Signals:    {len(signals)} collected, {len(signals) - len(triaged)} awaiting triage")
    typer.echo(f"Triage:     {by_disp['advance']} advanced / {by_disp['park']} parked / {by_disp['discard']} discarded")
    typer.echo(f"Ideas:      {len(ideas)} total, {len(scored)} scored, {len(briefed)} briefed")
    typer.echo(f"Decisions:  {len(decisions)} recorded")
    usage = store.read_jsonl(paths.llm_usage_file())
    in_tok = sum(u.get("input_tokens", 0) for u in usage)
    out_tok = sum(u.get("output_tokens", 0) for u in usage)
    typer.echo(f"LLM usage:  {len(usage)} calls, {in_tok:,} in / {out_tok:,} out tokens")


if __name__ == "__main__":
    app()
