"""Funding / M&A scanner - configurable news RSS feeds (source_class=funding)."""

from __future__ import annotations

from ..models import SignalRecord
from . import rss


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    feeds = config.get("funding", {}).get("feeds", [])
    for f in feeds:
        f.setdefault("source_class", "funding")
    return rss.scan_feeds(feeds, pcm, use_llm=use_llm)
