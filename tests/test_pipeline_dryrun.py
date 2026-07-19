"""End-to-end pipeline in dry-run mode: triage -> cluster -> score -> brief."""

from datetime import date

from cpi import store
from cpi.models import SignalRecord, SourceClass
from cpi.pipeline import brief as brief_mod
from cpi.pipeline import cluster as cluster_mod
from cpi.pipeline import score as score_mod
from cpi.pipeline import triage as triage_mod


def _seed_signals(n: int = 3):
    for i in range(n):
        store.save_signal(SignalRecord(
            id=f"sig{i:04d}aaaaaaaaaaaa", source_class=SourceClass.research,
            source_name="arXiv", url=f"https://arxiv.org/abs/26{i:02d}.0000{i}",
            collected_date=date.today(),
            title=f"Regime detection method {i}",
            summary=f"Paper {i} about market regime detection with change points.",
        ))


def test_full_dryrun_loop(cpi_home):
    _seed_signals()

    counts = triage_mod.run()
    assert counts["advance"] == 3  # dry-run triage advances everything
    assert len(store.untriaged_signals()) == 0

    ideas = cluster_mod.run()
    assert ideas, "clustering produced no ideas"
    assert set().union(*(set(i.signal_ids) for i in ideas)) == {f"sig{i:04d}aaaaaaaaaaaa" for i in range(3)}

    n = score_mod.run()
    assert n == len(ideas)

    path = brief_mod.run(month="2026-07")
    text = open(path, encoding="utf-8").read()
    assert "CPI Idea Brief" in text
    assert "## Cons & risks" in text

    # idempotent: re-running cluster on already-clustered signals creates nothing
    assert cluster_mod.run() == []


def test_discard_logged_never_deleted(cpi_home, monkeypatch):
    _seed_signals(1)
    from cpi import llm

    monkeypatch.setattr(llm, "_canned_json", lambda task, vars: {
        "disposition": "discard", "rationale": "off-topic", "confidence": 0.9,
        "re_review_trigger": None})
    triage_mod.run()
    from cpi import paths

    logs = list(paths.discards_dir().glob("*.jsonl"))
    assert logs and "off-topic" in logs[0].read_text()
    assert len(list(store.iter_signals())) == 1  # signal itself still present
