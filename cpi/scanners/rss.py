"""Generic RSS/Atom scanner - trade press, analyst blogs, competitor changelogs."""

from __future__ import annotations

import feedparser
import httpx

from .. import store
from ..models import SignalRecord, SourceClass
from . import base


def scan_feeds(feeds: list[dict], pcm, use_llm: bool = True) -> list[SignalRecord]:
    criteria = store.load_search_criteria()
    records: list[SignalRecord] = []
    for feed_cfg in feeds:
        name, url = feed_cfg["name"], feed_cfg["url"]
        source_class = SourceClass(feed_cfg.get("source_class", "industry"))
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  [rss] {name} failed: {e}")
            continue
        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not link or not title:
                continue
            rec = base.build_record(
                source_class=source_class, source_name=name, url=link,
                title=title, raw_excerpt=getattr(entry, "summary", ""),
                published=base.parse_date(getattr(entry, "published_parsed", None)),
                themes=pcm.watch_themes, use_llm=use_llm, criteria=criteria,
            )
            if rec:
                store.save_signal(rec)
                records.append(rec)
        base.polite_sleep()
    return records


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    return scan_feeds(config.get("rss", {}).get("feeds", []), pcm, use_llm=use_llm)
