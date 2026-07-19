"""Stage 1b - ground: search-criteria generation and scanner consumption."""

import pytest

from cpi import pcm as pcm_mod
from cpi import store
from cpi.models import SearchCriteria, ThemeSearch, WatchTheme
from cpi.pipeline import ground as ground_mod
from cpi.scanners import arxiv, base


def test_ground_generates_criteria_for_every_theme(cpi_home):
    path = ground_mod.run()
    assert path.endswith("search.yaml")

    criteria = store.load_search_criteria()
    assert criteria is not None
    theme_names = {t.name for t in pcm_mod.load().watch_themes}
    assert {t.theme for t in criteria.themes} == theme_names
    for t in criteria.themes:
        assert t.arxiv_queries and t.hn_keywords and t.press_keywords


def test_ground_standard_set_from_competitors(cpi_home):
    ground_mod.run()
    criteria = store.load_search_criteria()
    assert "CompetitorA" in criteria.standard_keywords
    # "Spreadsheets + manual checks" is a description, not a searchable name
    assert all(len(k.split()) <= 3 for k in criteria.standard_keywords)


def test_ground_refuses_silent_overwrite(cpi_home):
    ground_mod.run()
    with pytest.raises(SystemExit):
        ground_mod.run()
    ground_mod.run(force=True)  # explicit overwrite is fine


def test_theme_hints_match_translated_vocabulary(cpi_home):
    theme = WatchTheme(name="Data-quality monitoring", rationale="test",
                       keywords=["statistical process control for pipelines"])
    criteria = SearchCriteria(themes=[ThemeSearch(
        theme="Data-quality monitoring",
        press_keywords=["data downtime", "pipeline observability"],
    )])
    text = "Startup ships data downtime dashboards for analytics teams"
    assert base.theme_hints(text, [theme]) == []  # PCM phrasing alone misses
    assert base.theme_hints(text, [theme], criteria=criteria) == [
        "Data-quality monitoring"]


def test_arxiv_query_prefers_ground_phrases(cpi_home):
    theme = WatchTheme(name="T", rationale="test", arxiv_categories=["cs.DB"],
                       keywords=["our internal phrasing"])
    ts = ThemeSearch(theme="T", arxiv_queries=["data lineage", "schema evolution"])
    q = arxiv._query_for_theme(theme, ts)
    assert 'all:"data lineage"' in q and "cat:cs.DB" in q
    assert "internal phrasing" not in q
    # without criteria the PCM keywords still work (fallback)
    assert 'all:"our internal phrasing"' in arxiv._query_for_theme(theme, None)
