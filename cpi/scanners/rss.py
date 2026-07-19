"""Generic RSS/Atom scanner - trade press, analyst blogs, competitor changelogs.

Per-feed options (config/sources.yaml):
  require_theme_hint: true   skip items matching no watch theme (cost gate)
  expand_links: true         also create signals from outbound links in each
                             entry - turns digest/roundup posts into their
                             primary sources
"""

from __future__ import annotations

import html as html_mod
import re
from urllib.parse import urlparse

import feedparser
import httpx

from .. import store
from ..models import SignalRecord, SourceClass
from . import base

_LINK_RE = re.compile(r'<a\s[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
                      re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
MIN_ANCHOR_CHARS = 15   # shorter anchors are "here"/"read more"/nav noise
MAX_LINKS_PER_ENTRY = 10

_UA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def extract_links(entry_html: str, own_host: str) -> list[tuple[str, str]]:
    """(url, anchor_text) pairs for outbound links with descriptive anchors."""
    out = []
    for url, anchor in _LINK_RE.findall(entry_html or ""):
        text = html_mod.unescape(_TAG_RE.sub("", anchor)).strip()
        if len(text) < MIN_ANCHOR_CHARS:
            continue
        if urlparse(url).netloc == own_host:
            continue  # self-links back into the digest site
        out.append((url, text))
        if len(out) >= MAX_LINKS_PER_ENTRY:
            break
    return out


def _entry_outbound_links(entry, name: str, own_host: str) -> list[tuple[str, str]]:
    """Outbound links from feed summary/content, else from the entry's own page.

    Many digest feeds (WordPress excerpt mode) truncate the body so the actual
    links only exist on the page - one polite fetch recovers them.
    """
    for html_src in [getattr(entry, "summary", "") or "",
                     *[c.get("value", "") for c in getattr(entry, "content", [])]]:
        found = extract_links(html_src, own_host)
        if found:
            return found
    link = getattr(entry, "link", None)
    if not link:
        return []
    try:
        page = httpx.get(link, timeout=30, follow_redirects=True, headers=_UA_HEADERS)
        page.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [rss] {name}: expand fetch failed for {link}: {e}")
        return []
    finally:
        base.polite_sleep()
    return extract_links(page.text, own_host)


def scan_feeds(feeds: list[dict], pcm, use_llm: bool = True) -> list[SignalRecord]:
    criteria = store.load_search_criteria()
    records: list[SignalRecord] = []
    for feed_cfg in feeds:
        name, url = feed_cfg["name"], feed_cfg["url"]
        source_class = SourceClass(feed_cfg.get("source_class", "industry"))
        require_hint = bool(feed_cfg.get("require_theme_hint", False))
        expand = bool(feed_cfg.get("expand_links", False))
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True, headers=_UA_HEADERS)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  [rss] {name} failed: {e}")
            base.log_scan(name, 0, 0, str(e))
            continue
        feed = feedparser.parse(resp.content)
        feed_new = 0
        for entry in feed.entries:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not link or not title:
                continue
            published = base.parse_date(getattr(entry, "published_parsed", None))
            rec = base.build_record(
                source_class=source_class, source_name=name, url=link,
                title=title, raw_excerpt=getattr(entry, "summary", ""),
                published=published,
                themes=pcm.watch_themes, use_llm=use_llm, criteria=criteria,
                require_hint=require_hint,
            )
            if rec:
                store.save_signal(rec)
                records.append(rec)
                feed_new += 1
            if expand:
                for l_url, l_title in _entry_outbound_links(entry, name, urlparse(link).netloc):
                    sub = base.build_record(
                        source_class=source_class, source_name=f"{name} (links)",
                        url=l_url, title=l_title,
                        raw_excerpt=f"Linked from digest: {title}",
                        published=published, themes=pcm.watch_themes,
                        use_llm=use_llm, criteria=criteria, require_hint=require_hint,
                    )
                    if sub:
                        store.save_signal(sub)
                        records.append(sub)
                        feed_new += 1
        base.log_scan(name, len(feed.entries), feed_new)
        base.polite_sleep()
    return records


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    return scan_feeds(config.get("rss", {}).get("feeds", []), pcm, use_llm=use_llm)
