"""Stage 5 - Recommend: render the monthly ranked Idea Brief."""

from __future__ import annotations

import json
import re
from datetime import date

from .. import llm, paths, store
from .. import pcm as pcm_mod
from ..models import FACTORS, CandidateIdea
from .score import signals_block

MAX_IDEAS = 5          # hard cap by rule
CONS_MIN_RATIO = 0.7   # cons word-count must be >= 70% of pros word-count


class BriefValidationError(Exception):
    pass


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^##\s*{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                  text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def validate_page(page: str) -> None:
    """Reject a page whose cons are materially weaker than its pros."""
    required = ["The idea", "The signal", "Why now", "Cost of inaction",
                "Pros", "Cons & risks", "Suggested next step"]
    for h in required:
        if not _section(page, h):
            raise BriefValidationError(f"missing or empty section: {h}")
    pros_words = len(_section(page, "Pros").split())
    cons_words = len(_section(page, "Cons & risks").split())
    if cons_words < CONS_MIN_RATIO * pros_words:
        raise BriefValidationError(
            f"cons section too weak: {cons_words} words vs {pros_words} in pros "
            f"(minimum ratio {CONS_MIN_RATIO})"
        )


def ranked_candidates(month: str) -> list[tuple[CandidateIdea, float]]:
    weights = store.load_weights()
    scored = []
    for idea in store.iter_ideas():
        s = idea.effective_scores()
        if s is None:
            continue
        if idea.briefed_in and idea.briefed_in != month:
            continue  # already delivered in an earlier brief
        scored.append((idea, s.weighted_total(weights)))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:MAX_IDEAS]


def draft_page(idea: CandidateIdea, total: float, rank: int, pcm_block: str) -> str:
    s = idea.effective_scores()
    page = llm.complete(
        "brief", pcm_block=pcm_block, rank=rank, weighted_total=total,
        title=idea.title, summary=idea.summary,
        scores_json=json.dumps({f: getattr(s, f) for f in FACTORS}),
        signals_block=signals_block(idea),
    )
    try:
        validate_page(page)
    except BriefValidationError as e:
        # one retry with the failure fed back; then hard-fail the page
        print(f"  [brief] {idea.id} rejected ({e}); retrying once")
        page = llm.complete(
            "brief", pcm_block=pcm_block, rank=rank, weighted_total=total,
            title=idea.title,
            summary=idea.summary + f"\n\nPREVIOUS DRAFT REJECTED: {e}. "
            "Cons must match pros in force and specificity.",
            scores_json=json.dumps({f: getattr(s, f) for f in FACTORS}),
            signals_block=signals_block(idea),
        )
        validate_page(page)
    return page


def run(month: str | None = None) -> str:
    month = month or date.today().strftime("%Y-%m")
    p = pcm_mod.load()
    block = pcm_mod.render_prompt_block(p)

    candidates = ranked_candidates(month)
    if not candidates:
        raise SystemExit("No scored ideas to brief. Run: cpi cluster && cpi score")

    parts = [f"# CPI Idea Brief — {p.product_name} — {month}",
             f"\n_{len(candidates)} idea(s), ranked. Hard cap {MAX_IDEAS}; excess queues for next cycle._\n"]
    for rank, (idea, total) in enumerate(candidates, 1):
        s = idea.effective_scores()
        table = "| " + " | ".join(FACTORS) + " | weighted |\n"
        table += "|" + "---|" * (len(FACTORS) + 1) + "\n"
        table += "| " + " | ".join(str(getattr(s, f)) for f in FACTORS) + f" | **{total}** |"
        page = draft_page(idea, total, rank, block)
        parts.append(f"\n---\n\n# {rank}. {idea.title}  `{idea.id}`\n\n{table}\n\n{page}")
        idea.briefed_in = month
        store.save_idea(idea)

    out = paths.briefs_dir() / f"{month}-idea-brief.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return str(out)
