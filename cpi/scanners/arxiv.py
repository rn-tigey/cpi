"""arXiv scanner - export API, driven by PCM watch-theme categories/keywords."""

from __future__ import annotations

from datetime import date, timedelta

import feedparser
import httpx

from .. import store
from ..models import SignalRecord, SourceClass
from . import base

API = "https://export.arxiv.org/api/query"


def _query_for_theme(theme, theme_search=None) -> str | None:
    parts = []
    if theme.arxiv_categories:
        parts.append("(" + " OR ".join(f"cat:{c}" for c in theme.arxiv_categories) + ")")
    # `cpi ground` phrases beat raw PCM keywords - they are written in paper language
    phrases = (theme_search.arxiv_queries if theme_search and theme_search.arxiv_queries
               else theme.keywords)[:4]
    if phrases:
        parts.append("(" + " OR ".join(f'all:"{k}"' for k in phrases) + ")")
    if not parts:
        return None
    return " AND ".join(parts)


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    cfg = config.get("arxiv", {})
    max_results = cfg.get("max_results_per_theme", 25)
    lookback = cfg.get("lookback_days", 7)
    cutoff = date.today() - timedelta(days=lookback)
    criteria = store.load_search_criteria()

    records: list[SignalRecord] = []
    fetched = 0
    errors: list[str] = []
    for theme in pcm.watch_themes:
        query = _query_for_theme(theme, criteria.for_theme(theme.name) if criteria else None)
        if not query:
            continue
        try:
            resp = httpx.get(API, params={
                "search_query": query, "sortBy": "submittedDate",
                "sortOrder": "descending", "max_results": max_results,
            }, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  [arxiv] theme '{theme.name}' failed: {e}")
            errors.append(f"{theme.name}: {e}")
            continue
        feed = feedparser.parse(resp.text)
        fetched += len(feed.entries)
        for entry in feed.entries:
            published = base.parse_date(getattr(entry, "published_parsed", None))
            if published and published < cutoff:
                continue
            rec = base.build_record(
                source_class=SourceClass.research, source_name="arXiv",
                url=entry.link, title=entry.title.replace("\n", " "),
                raw_excerpt=getattr(entry, "summary", ""),
                published=published, themes=pcm.watch_themes, use_llm=use_llm,
                criteria=criteria, require_hint=bool(cfg.get("require_theme_hint", False)),
            )
            if rec:
                store.save_signal(rec)
                records.append(rec)
        base.polite_sleep()
    base.log_scan("arXiv", fetched, len(records), "; ".join(errors) or None)
    return records
