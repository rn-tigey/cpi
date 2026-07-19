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
    theme = WatchTheme(name="Uncertainty quantification", rationale="test",
                       keywords=["adaptive conformal inference"])
    criteria = SearchCriteria(themes=[ThemeSearch(
        theme="Uncertainty quantification",
        press_keywords=["confidence intervals", "model uncertainty"],
    )])
    text = "Startup ships model uncertainty dashboards for ML teams"
    assert base.theme_hints(text, [theme]) == []  # PCM phrasing alone misses
    assert base.theme_hints(text, [theme], criteria=criteria) == [
        "Uncertainty quantification"]


def test_arxiv_query_prefers_ground_phrases(cpi_home):
    theme = WatchTheme(name="T", rationale="test", arxiv_categories=["cs.LG"],
                       keywords=["our internal phrasing"])
    ts = ThemeSearch(theme="T", arxiv_queries=["distribution shift", "domain adaptation"])
    q = arxiv._query_for_theme(theme, ts)
    assert 'all:"distribution shift"' in q and "cat:cs.LG" in q
    assert "internal phrasing" not in q
    # without criteria the PCM keywords still work (fallback)
    assert 'all:"our internal phrasing"' in arxiv._query_for_theme(theme, None)
