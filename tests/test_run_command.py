"""`cpi run` - the one-shot cycle command (scan skipped via empty source list)."""

from datetime import date

from cpi import cli, paths, store
from cpi.models import SignalRecord, SourceClass


def _seed(n=3):
    for i in range(n):
        store.save_signal(SignalRecord(
            id=f"run{i:04d}aaaaaaaaaaaa", source_class=SourceClass.research,
            source_name="arXiv", url=f"https://example.org/run/{i}",
            collected_date=date.today(),
            title=f"Anomaly detection advance {i}",
            summary=f"Paper {i} on detection methods for data pipelines.",
        ))


def test_run_produces_brief_from_seeded_signals(cpi_home):
    _seed()
    cli.run(source="", no_llm=True)  # dry-run LLM advances everything
    briefs = list(paths.briefs_dir().glob("*-idea-brief.md"))
    assert len(briefs) == 1
    assert "CPI Idea Brief" in briefs[0].read_text(encoding="utf-8")


def test_run_is_graceful_with_nothing_to_brief(cpi_home, capsys):
    cli.run(source="", no_llm=True)  # empty home: no signals at all
    out = capsys.readouterr().out
    assert "no scored ideas to brief yet" in out
    assert not list(paths.briefs_dir().glob("*.md"))
