"""Pydantic data models: signal records, triage, ideas, scores, decisions, PCM."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Signals ────────────────────────────────────────────────────────────────

class SourceClass(str, Enum):
    research = "research"
    industry = "industry"
    competitor = "competitor"
    community = "community"
    funding = "funding"


def url_hash(url: str) -> str:
    normalized = url.strip().rstrip("/").lower()
    return hashlib.sha1(normalized.encode()).hexdigest()[:16]


class SignalRecord(BaseModel):
    id: str
    source_class: SourceClass
    source_name: str
    url: str
    published_date: Optional[date] = None
    collected_date: date
    title: str
    summary: str = ""
    claimed_significance: str = ""
    raw_excerpt: str = ""
    watch_theme_hints: list[str] = Field(default_factory=list)

    @classmethod
    def make_id(cls, url: str) -> str:
        return url_hash(url)


# ── Triage ─────────────────────────────────────────────────────────────────

class Disposition(str, Enum):
    advance = "advance"
    park = "park"
    discard = "discard"


class TriageResult(BaseModel):
    signal_id: str
    disposition: Disposition
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    re_review_trigger: Optional[str] = None
    triaged_at: datetime
    model: str


# ── Ideas & scoring ────────────────────────────────────────────────────────

FACTORS = ("impact", "strategic_fit", "effort", "timing", "confidence")


class FactorScores(BaseModel):
    """1-5 per factor. `effort` is already inverted: lower effort => higher score."""

    impact: int = Field(ge=1, le=5)
    strategic_fit: int = Field(ge=1, le=5)
    effort: int = Field(ge=1, le=5)
    timing: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    justifications: dict[str, str] = Field(default_factory=dict)

    def weighted_total(self, weights: dict[str, float]) -> float:
        return round(sum(getattr(self, f) * weights[f] for f in FACTORS), 3)


class CandidateIdea(BaseModel):
    id: str
    title: str
    summary: str
    signal_ids: list[str]
    created_date: date
    draft_scores: Optional[FactorScores] = None
    final_scores: Optional[FactorScores] = None
    score_model: Optional[str] = None
    briefed_in: Optional[str] = None  # YYYY-MM of the brief it appeared in

    def effective_scores(self) -> Optional[FactorScores]:
        return self.final_scores or self.draft_scores


class Decision(BaseModel):
    idea_id: str
    disposition: str  # fund | park | kill
    note: str = ""
    decided_at: datetime

    @field_validator("disposition")
    @classmethod
    def _check_disposition(cls, v: str) -> str:
        if v not in ("fund", "park", "kill"):
            raise ValueError("disposition must be fund, park, or kill")
        return v


# ── Product Context Model ──────────────────────────────────────────────────

class Capability(BaseModel):
    name: str
    description: str
    maturity: str  # e.g. nascent | maturing | mature


class WatchTheme(BaseModel):
    name: str
    rationale: str
    arxiv_categories: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class StrategyFrame(BaseModel):
    where_we_win: list[str]
    non_goals: list[str]
    roadmap_themes: list[str] = Field(default_factory=list)


class PCM(BaseModel):
    product_name: str
    version: str = "1"
    capability_map: list[Capability]
    user_and_job_model: dict
    strategy_frame: StrategyFrame
    technical_posture: dict
    competitive_set: list[dict]
    watch_themes: list[WatchTheme]

    @model_validator(mode="after")
    def _check_watch_themes(self) -> "PCM":
        if not (1 <= len(self.watch_themes) <= 12):
            raise ValueError("watch_themes should contain between 1 and 12 themes (5-10 recommended)")
        return self
