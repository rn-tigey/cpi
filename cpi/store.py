"""File-based storage: signals, triage results, ideas, decisions, logs.

Everything is JSON/JSONL under data/ - git-friendly, no database.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import yaml

from . import paths
from .models import FACTORS, CandidateIdea, Decision, SignalRecord, TriageResult

# ── seen-URL dedupe index ──────────────────────────────────────────────────

def load_seen() -> set[str]:
    f = paths.seen_urls_file()
    if not f.exists():
        return set()
    return set(f.read_text(encoding="utf-8").split())


def mark_seen(signal_id: str) -> None:
    paths.data_dir().mkdir(parents=True, exist_ok=True)
    with open(paths.seen_urls_file(), "a", encoding="utf-8") as f:
        f.write(signal_id + "\n")


# ── signals ────────────────────────────────────────────────────────────────

def week_bucket(d: date | None = None) -> str:
    d = d or date.today()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def save_signal(rec: SignalRecord) -> Path:
    folder = paths.signals_dir() / week_bucket(rec.collected_date)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{rec.id}.json"
    path.write_text(rec.model_dump_json(indent=2), encoding="utf-8")
    mark_seen(rec.id)
    return path

def iter_signals():
    root = paths.signals_dir()
    if not root.exists():
        return
    for p in sorted(root.rglob("*.json")):
        yield SignalRecord.model_validate_json(p.read_text(encoding="utf-8"))


def get_signal(signal_id: str) -> SignalRecord | None:
    for p in paths.signals_dir().rglob(f"{signal_id}.json"):
        return SignalRecord.model_validate_json(p.read_text(encoding="utf-8"))
    return None


# ── triage ─────────────────────────────────────────────────────────────────

def save_triage(result: TriageResult) -> None:
    paths.triage_dir().mkdir(parents=True, exist_ok=True)
    path = paths.triage_dir() / f"{result.signal_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    if result.disposition.value == "discard":
        log = paths.discards_dir() / f"{week_bucket()}.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")


def get_triage(signal_id: str) -> TriageResult | None:
    path = paths.triage_dir() / f"{signal_id}.json"
    if not path.exists():
        return None
    return TriageResult.model_validate_json(path.read_text(encoding="utf-8"))


def iter_triage():
    root = paths.triage_dir()
    if not root.exists():
        return
    for p in sorted(root.glob("*.json")):
        yield TriageResult.model_validate_json(p.read_text(encoding="utf-8"))


def signals_by_disposition(disposition: str) -> list[SignalRecord]:
    ids = [t.signal_id for t in iter_triage() if t.disposition.value == disposition]
    out = []
    for sid in ids:
        s = get_signal(sid)
        if s:
            out.append(s)
    return out


def untriaged_signals() -> list[SignalRecord]:
    return [s for s in iter_signals() if get_triage(s.id) is None]


# ── ideas ──────────────────────────────────────────────────────────────────

def save_idea(idea: CandidateIdea) -> None:
    paths.ideas_dir().mkdir(parents=True, exist_ok=True)
    (paths.ideas_dir() / f"{idea.id}.json").write_text(idea.model_dump_json(indent=2), encoding="utf-8")


def get_idea(idea_id: str) -> CandidateIdea | None:
    path = paths.ideas_dir() / f"{idea_id}.json"
    if not path.exists():
        return None
    return CandidateIdea.model_validate_json(path.read_text(encoding="utf-8"))


def iter_ideas():
    root = paths.ideas_dir()
    if not root.exists():
        return
    for p in sorted(root.glob("*.json")):
        yield CandidateIdea.model_validate_json(p.read_text(encoding="utf-8"))


def clustered_signal_ids() -> set[str]:
    ids: set[str] = set()
    for idea in iter_ideas():
        ids.update(idea.signal_ids)
    return ids


# ── decisions & calibration logs ───────────────────────────────────────────

def append_decision(decision: Decision) -> None:
    paths.decisions_dir().mkdir(parents=True, exist_ok=True)
    with open(paths.decisions_dir() / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(decision.model_dump_json() + "\n")


def iter_decisions() -> list[Decision]:
    path = paths.decisions_dir() / "decisions.jsonl"
    if not path.exists():
        return []
    return [Decision.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ── config ─────────────────────────────────────────────────────────────────

def load_weights() -> dict[str, float]:
    with open(paths.config_dir() / "weights.yaml", "r", encoding="utf-8") as f:
        weights = yaml.safe_load(f)
    total = sum(weights[f] for f in FACTORS)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0 (got {total})")
    return weights


def load_sources() -> dict:
    with open(paths.config_dir() / "sources.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
