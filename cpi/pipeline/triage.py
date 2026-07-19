"""Stage 3 - Filter: LLM triage of signals against the PCM."""

from __future__ import annotations

from datetime import datetime, timezone

from .. import llm, store
from .. import pcm as pcm_mod
from ..models import Disposition, SignalRecord, TriageResult

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "disposition": {"type": "string", "enum": ["advance", "park", "discard"]},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
        "re_review_trigger": {"type": ["string", "null"]},
    },
    "required": ["disposition", "rationale", "confidence", "re_review_trigger"],
    "additionalProperties": False,
}


def triage_signal(signal: SignalRecord, pcm_block: str) -> TriageResult:
    out = llm.complete_json(
        "triage", TRIAGE_SCHEMA,
        pcm_block=pcm_block,
        source_name=signal.source_name, source_class=signal.source_class.value,
        published_date=str(signal.published_date or "unknown"),
        title=signal.title, summary=signal.summary,
        claimed_significance=signal.claimed_significance, url=signal.url,
    )
    disposition = Disposition(out["disposition"])
    trigger = out.get("re_review_trigger")
    if disposition == Disposition.park and not trigger:
        trigger = "revisit at next monthly parked-queue re-score"
    return TriageResult(
        signal_id=signal.id, disposition=disposition,
        rationale=out["rationale"],
        confidence=max(0.0, min(1.0, float(out["confidence"]))),
        re_review_trigger=trigger,
        triaged_at=datetime.now(timezone.utc),
        model="dry-run" if llm.dry_run() else llm.TASK_MODELS["triage"],
    )


def run(limit: int | None = None, rescore_parked: bool = False) -> dict:
    """Triage untriaged signals (or re-score the parked queue). Returns counts."""
    p = pcm_mod.load()
    block = pcm_mod.render_prompt_block(p)

    if rescore_parked:
        targets = store.signals_by_disposition("park")
    else:
        targets = store.untriaged_signals()
    if limit:
        targets = targets[:limit]

    counts = {"advance": 0, "park": 0, "discard": 0, "errors": 0}
    for signal in targets:
        try:
            result = triage_signal(signal, block)
        except Exception as e:
            print(f"  [triage] {signal.id} failed: {e}")
            counts["errors"] += 1
            continue
        store.save_triage(result)
        counts[result.disposition.value] += 1
        print(f"  {result.disposition.value:8s} {signal.title[:70]}")
    return counts
