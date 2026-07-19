"""Brief page validation: pros/cons symmetry and the 5-idea cap."""

from datetime import date

import pytest

from cpi import store
from cpi.models import CandidateIdea, FactorScores
from cpi.pipeline import brief as brief_mod

GOOD_PAGE = """## The idea
One sentence.

## The signal
Observed things, https://example.com

## Why now
Timing.

## Cost of inaction
Cost.

## Pros
- Strong pro one with detail (impact)
- Strong pro two with detail (timing)
- Strong pro three with detail (fit)

## Cons & risks
- Strong con one with equal detail and force
- Strong con two with equal detail and force
- Strong con three with equal detail and force

## Suggested next step
A two-day probe.
"""


def test_valid_page_passes():
    brief_mod.validate_page(GOOD_PAGE)


def test_weak_cons_rejected():
    weak = GOOD_PAGE.replace(
        "- Strong con one with equal detail and force\n"
        "- Strong con two with equal detail and force\n"
        "- Strong con three with equal detail and force",
        "- meh",
    )
    with pytest.raises(brief_mod.BriefValidationError, match="cons section too weak"):
        brief_mod.validate_page(weak)


def test_missing_section_rejected():
    no_next_step = GOOD_PAGE.replace("## Suggested next step\nA two-day probe.\n", "")
    with pytest.raises(brief_mod.BriefValidationError, match="missing"):
        brief_mod.validate_page(no_next_step)


def _mk_idea(i: int) -> CandidateIdea:
    return CandidateIdea(
        id=f"idea-202607-{i:03d}", title=f"Idea {i}", summary="s",
        signal_ids=[], created_date=date.today(),
        draft_scores=FactorScores(impact=i % 5 + 1, strategic_fit=3, effort=3,
                                  timing=3, confidence=3),
    )


def test_five_idea_cap(cpi_home):
    for i in range(1, 9):  # 8 scored ideas
        store.save_idea(_mk_idea(i))
    ranked = brief_mod.ranked_candidates("2026-07")
    assert len(ranked) == brief_mod.MAX_IDEAS == 5
    totals = [t for _, t in ranked]
    assert totals == sorted(totals, reverse=True)
