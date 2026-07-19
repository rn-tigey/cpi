"""Hacker News scanner - Algolia search API on PCM watch-theme keywords."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import httpx

from .. import store
from ..models import SignalRecord, SourceClass
from . import base

API = "https://hn.algolia.com/api/v1/search_by_date"


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    cfg = config.get("hn", {})
    lookback = cfg.get("lookback_days", 7)
    min_points = cfg.get("min_points", 10)
    since = int(time.mktime((datetime.now() - timedelta(days=lookback)).timetuple()))

    keywords: list[str] = list(cfg.get("extra_keywords", []))
    for theme in pcm.watch_themes:
        keywords.extend(theme.keywords[:2])

    records: list[SignalRecord] = []
    for kw in dict.fromkeys(keywords):  # preserve order, dedupe
        try:
            resp = httpx.get(API, params={
                "query": kw, "tags": "story",
                "numericFilters": f"created_at_i>{since},points>={min_points}",
                "hitsPerPage": 20,
            }, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  [hn] keyword '{kw}' failed: {e}")
            continue
        for hit in resp.json().get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            title = hit.get("title") or ""
            if not title:
                continue
            created = hit.get("created_at", "")[:10]
            excerpt = (hit.get("story_text") or "")
            comment_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
            rec = base.build_record(
                source_class=SourceClass.community, source_name="Hacker News",
                url=url, title=title,
                raw_excerpt=f"{excerpt}\n[{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments: {comment_url}]",
                published=created, themes=pcm.watch_themes, use_llm=use_llm,
            )
            if rec:
                store.save_signal(rec)
                records.append(rec)
        base.polite_sleep()
    return records
