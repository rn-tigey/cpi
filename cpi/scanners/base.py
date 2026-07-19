"""Shared scanner machinery: normalization, dedupe, rate limiting, LLM summaries."""

from __future__ import annotations

import json
import time
from datetime import date, datetime

from .. import llm, store
from ..models import SignalRecord, SourceClass

# Above this size we consider an item "long-form" and pay one Haiku call for a
# proper summary; below it, a deterministic truncation is good enough.
LONGFORM_CHARS = 1200
REQUEST_DELAY_S = 1.0  # polite spacing between HTTP requests within a scanner


def polite_sleep() -> None:
    time.sleep(REQUEST_DELAY_S)


def log_scan(source_name: str, fetched: int, new: int, error: str | None = None) -> None:
    """One row per source per scan run - feeds the health table in `cpi status`."""
    from .. import paths

    store.append_jsonl(paths.scan_log_file(), {
        "source": source_name, "fetched": fetched, "new": new, "error": error,
    })


def parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, time.struct_time):
        return date(*value[:3])
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S"):
        try:
            return datetime.strptime(str(value)[: len(fmt) + 2].strip(), fmt).date()
        except ValueError:
            continue
    return None


def theme_hints(text: str, themes: list, criteria=None) -> list[str]:
    """Cheap keyword-overlap hints; the triage LLM does the real judgment.

    With `cpi ground` criteria present, each theme also matches on its
    channel-translated vocabulary - PCM keywords alone are usually phrased
    too academically to appear verbatim in headlines.
    """
    lowered = text.lower()
    hits = []
    for t in themes:
        terms = [*t.keywords, t.name]
        if criteria is not None:
            terms += criteria.all_theme_terms(t.name)
        if any(term.lower() in lowered for term in terms if term):
            hits.append(t.name)
    return hits


def summarize(rec: SignalRecord, use_llm: bool = True) -> SignalRecord:
    """Fill summary/claimed_significance - via Haiku for long-form, else truncation."""
    excerpt = (rec.raw_excerpt or "").strip()
    if use_llm and len(excerpt) >= LONGFORM_CHARS:
        try:
            out = llm.complete("summarize", source_name=rec.source_name,
                               source_class=rec.source_class.value, title=rec.title,
                               url=rec.url, raw_excerpt=excerpt[:6000])
            data = json.loads(out) if out.strip().startswith("{") else {}
            rec.summary = data.get("summary") or excerpt[:400]
            rec.claimed_significance = data.get("claimed_significance", "")
            return rec
        except Exception:
            pass  # fall through to truncation - a scan must never die on one item
    rec.summary = rec.summary or excerpt[:400] or rec.title
    return rec


def build_record(*, source_class: SourceClass, source_name: str, url: str,
                 title: str, raw_excerpt: str, published, themes: list,
                 use_llm: bool = True, criteria=None,
                 require_hint: bool = False) -> SignalRecord | None:
    """Normalize one collected item into a SignalRecord; None if already seen.

    With require_hint, items matching no watch theme are skipped BEFORE the
    LLM summary call - a cost gate for high-noise feeds. Skipped items are not
    marked seen, so they get another chance if the criteria later improve.
    """
    sid = SignalRecord.make_id(url)
    if sid in store.load_seen():
        return None
    hints = theme_hints(f"{title} {raw_excerpt}", themes, criteria=criteria)
    if require_hint and not hints:
        return None
    rec = SignalRecord(
        id=sid, source_class=source_class, source_name=source_name, url=url,
        published_date=parse_date(published), collected_date=date.today(),
        title=title.strip(), raw_excerpt=(raw_excerpt or "").strip()[:8000],
        watch_theme_hints=hints,
    )
    return summarize(rec, use_llm=use_llm)
