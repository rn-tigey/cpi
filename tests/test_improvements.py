"""Feed health, source scorecard, link expansion, hint gate, cluster threshold, init."""

from datetime import date, datetime, timezone
from pathlib import Path

from cpi import paths, store
from cpi.models import Disposition, SignalRecord, SourceClass, TriageResult
from cpi.pipeline import learn
from cpi.pipeline.cluster import _cluster_texts
from cpi.scanners import base, rss


def _signal(i: int, source: str) -> SignalRecord:
    return SignalRecord(
        id=f"sig{i:04d}bbbbbbbbbbbb", source_class=SourceClass.industry,
        source_name=source, url=f"https://example.com/{source}/{i}",
        collected_date=date.today(), title=f"Item {i}", summary=f"Summary {i}.",
    )


def _triage(signal_id: str, disposition: str) -> TriageResult:
    return TriageResult(signal_id=signal_id, disposition=Disposition(disposition),
                        rationale="t", confidence=0.5,
                        triaged_at=datetime.now(timezone.utc), model="test")


# ── #1 feed health ─────────────────────────────────────────────────────────

def test_source_health_tracks_zero_streaks_and_errors(cpi_home):
    base.log_scan("GoodFeed", 10, 3)
    for _ in range(4):
        base.log_scan("DeadFeed", 5, 0)
    base.log_scan("BrokenFeed", 0, 0, error="403 Forbidden")

    health = {h["source"]: h for h in store.source_health()}
    assert health["GoodFeed"]["zero_streak"] == 0
    assert health["GoodFeed"]["total_new"] == 3
    assert health["DeadFeed"]["zero_streak"] == 4
    assert health["BrokenFeed"]["last_error"] == "403 Forbidden"


# ── #2 source scorecard ────────────────────────────────────────────────────

def test_scorecard_ranks_sources_and_flags_prune_candidates(cpi_home):
    for i in range(10):  # NoisyFeed: 10 triaged, zero advanced -> prune candidate
        store.save_signal(_signal(i, "NoisyFeed"))
        store.save_triage(_triage(f"sig{i:04d}bbbbbbbbbbbb", "discard"))
    store.save_signal(_signal(10, "GoodFeed"))
    store.save_triage(_triage("sig0010bbbbbbbbbbbb", "advance"))

    rows = store.source_scorecard()
    assert rows[0]["source"] == "GoodFeed" and rows[0]["advance_rate"] == 1.0
    assert rows[-1]["source"] == "NoisyFeed" and rows[-1]["advance_rate"] == 0.0

    block, prune = learn._scorecard_block()
    assert prune == ["NoisyFeed"]
    assert "Prune candidates" in block and "GoodFeed" not in " ".join(prune)


# ── #3 digest link expansion ───────────────────────────────────────────────

def test_extract_links_keeps_descriptive_outbound_anchors():
    html = (
        '<p><a href="https://papers.example.org/anomaly-study">'
        "A Long Descriptive Paper Title &amp; Findings</a>"
        ' <a href="https://digest.example.com/self-post">Self link with long text here</a>'
        ' <a href="https://elsewhere.example.net/x">here</a></p>'
    )
    links = rss.extract_links(html, own_host="digest.example.com")
    assert links == [("https://papers.example.org/anomaly-study",
                      "A Long Descriptive Paper Title & Findings")]


# ── #6 require_theme_hint gate ─────────────────────────────────────────────

def test_require_hint_skips_unmatched_items_without_marking_seen(cpi_home):
    from cpi import pcm as pcm_mod
    themes = pcm_mod.load().watch_themes
    kwargs = dict(source_class=SourceClass.industry, source_name="T",
                  url="https://example.com/offtopic", title="Celebrity gossip news",
                  raw_excerpt="nothing relevant", published=None, themes=themes)
    assert base.build_record(**kwargs, require_hint=True) is None
    assert SignalRecord.make_id("https://example.com/offtopic") not in store.load_seen()
    # same item passes without the gate
    assert base.build_record(**kwargs, require_hint=False) is not None


# ── #4 cluster threshold ───────────────────────────────────────────────────

def test_cluster_threshold_controls_merging():
    texts = ["alpha beta gamma delta epsilon", "zeta eta theta iota kappa"]
    assert len(set(_cluster_texts(texts))) == 2          # default: no shared terms
    assert len(set(_cluster_texts(texts, threshold=1.5))) == 1  # forced merge


# ── #5 packaging: init seeds homes from packaged templates ─────────────────

def test_init_seeds_home_from_packaged_templates(tmp_path, monkeypatch):
    from cpi import cli
    dest = tmp_path / "newhome"
    cli.init(dest=dest)
    for expected in ("context/pcm.yaml", "context/pcm.template.yaml",
                     "config/sources.yaml", "config/weights.yaml",
                     "prompts/triage.md", "prompts/ground.md"):
        assert (dest / Path(expected)).exists(), f"missing {expected}"
    assert paths.templates_dir().is_dir()
