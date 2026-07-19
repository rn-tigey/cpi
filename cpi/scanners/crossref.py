"""Crossref scanner - published academic literature, all fields, DOI-indexed.

Complements arXiv (STEM preprints): Crossref covers journal articles and
conference proceedings across every discipline. Free API, no key; set
`mailto` in config to join the polite pool (faster, more reliable).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import httpx

from .. import store
from ..models import SignalRecord, SourceClass
from . import base

API = "https://api.crossref.org/works"

_JATS_RE = re.compile(r"<[^>]+>")


def _strip_jats(text: str) -> str:
    """Crossref abstracts arrive as JATS XML - strip to plain text."""
    return _JATS_RE.sub(" ", text or "").strip()


def _pub_date(item: dict) -> date | None:
    parts = (item.get("published") or {}).get("date-parts") or []
    if parts and parts[0] and parts[0][0]:
        p = list(parts[0]) + [1, 1]  # year-only / year-month dates
        try:
            return date(p[0], p[1], p[2])
        except (ValueError, TypeError):
            return None
    return None


def scan(pcm, config: dict, use_llm: bool = True) -> list[SignalRecord]:
    cfg = config.get("crossref", {})
    max_results = cfg.get("max_results_per_theme", 15)
    lookback = cfg.get("lookback_days", 30)
    mailto = cfg.get("mailto", "")
    today = date.today()
    cutoff = today - timedelta(days=lookback)
    criteria = store.load_search_criteria()

    records: list[SignalRecord] = []
    fetched = 0
    errors: list[str] = []
    for theme in pcm.watch_themes:
        ts = criteria.for_theme(theme.name) if criteria else None
        phrases = (ts.arxiv_queries if ts and ts.arxiv_queries else theme.keywords)[:3]
        if not phrases:
            continue
        params = {
            "query": " ".join(f'"{p}"' for p in phrases),
            "filter": f"from-pub-date:{cutoff.isoformat()},until-pub-date:{today.isoformat()}",
            "sort": "published", "order": "desc", "rows": max_results,
        }
        if mailto:
            params["mailto"] = mailto
        try:
            resp = httpx.get(API, params=params, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  [crossref] theme '{theme.name}' failed: {e}")
            errors.append(f"{theme.name}: {e}")
            continue
        items = resp.json().get("message", {}).get("items", [])
        fetched += len(items)
        for item in items:
            title = " ".join((item.get("title") or [""])[0].split())
            url = item.get("URL") or (item.get("DOI") and f"https://doi.org/{item['DOI']}")
            if not title or not url:
                continue
            rec = base.build_record(
                source_class=SourceClass.research, source_name="Crossref",
                url=url, title=title,
                raw_excerpt=_strip_jats(item.get("abstract", "")),
                published=_pub_date(item), themes=pcm.watch_themes,
                use_llm=use_llm, criteria=criteria,
                require_hint=bool(cfg.get("require_theme_hint", False)),
            )
            if rec:
                store.save_signal(rec)
                records.append(rec)
        base.polite_sleep()
    base.log_scan("Crossref", fetched, len(records), "; ".join(errors) or None)
    return records
