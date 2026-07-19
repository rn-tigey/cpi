"""Scanner normalization and URL dedupe."""

from cpi import pcm as pcm_mod
from cpi import store
from cpi.models import SourceClass
from cpi.scanners import base


def test_normalize_builds_record(cpi_home):
    p = pcm_mod.load()
    rec = base.build_record(
        source_class=SourceClass.research, source_name="arXiv",
        url="https://arxiv.org/abs/2501.00001",
        title="LLM-driven root cause analysis for observability pipelines",
        raw_excerpt="We study large language models that explain metric anomalies end to end.",
        published="2026-07-01", themes=p.watch_themes, use_llm=False,
    )
    assert rec is not None
    assert rec.id == rec.make_id("https://arxiv.org/abs/2501.00001")
    assert rec.published_date.isoformat() == "2026-07-01"
    assert rec.summary  # filled by truncation path
    assert "LLM-based root cause analysis" in rec.watch_theme_hints


def test_dedupe_on_url(cpi_home):
    p = pcm_mod.load()
    kwargs = dict(source_class=SourceClass.community, source_name="HN",
                  url="https://example.com/story", title="A story",
                  raw_excerpt="text", published=None, themes=p.watch_themes, use_llm=False)
    first = base.build_record(**kwargs)
    assert first is not None
    store.save_signal(first)
    # trailing slash / case variations hash identically
    kwargs["url"] = "https://EXAMPLE.com/story/"
    assert base.build_record(**kwargs) is None


def test_bad_date_tolerated(cpi_home):
    p = pcm_mod.load()
    rec = base.build_record(source_class=SourceClass.industry, source_name="RSS",
                            url="https://example.com/x", title="t", raw_excerpt="",
                            published="not-a-date", themes=p.watch_themes, use_llm=False)
    assert rec.published_date is None
