"""Stage 4b - Score candidate ideas (LLM drafts, human reviews)."""

from __future__ import annotations

from .. import llm, paths, store
from .. import pcm as pcm_mod
from ..models import FACTORS, CandidateIdea, FactorScores

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        **{f: {"type": "integer", "enum": [1, 2, 3, 4, 5]} for f in FACTORS},
        "justifications": {
            "type": "object",
            "properties": {f: {"type": "string"} for f in FACTORS},
            "required": list(FACTORS),
            "additionalProperties": False,
        },
    },
    "required": [*FACTORS, "justifications"],
    "additionalProperties": False,
}


def signals_block(idea: CandidateIdea) -> str:
    lines = []
    for sid in idea.signal_ids:
        s = store.get_signal(sid)
        if s:
            lines.append(f"- [{s.source_class.value}/{s.source_name}] {s.title}\n"
                         f"  {s.summary}\n  {s.url}")
    return "\n".join(lines) or "(signals unavailable)"


def draft_scores(idea: CandidateIdea, pcm_block: str) -> FactorScores:
    out = llm.complete_json("score", SCORE_SCHEMA, pcm_block=pcm_block,
                            title=idea.title, summary=idea.summary,
                            signals_block=signals_block(idea))
    return FactorScores(**out)


def run(rescore: bool = False) -> int:
    p = pcm_mod.load()
    block = pcm_mod.render_prompt_block(p)
    n = 0
    for idea in store.iter_ideas():
        if idea.draft_scores is not None and not rescore:
            continue
        idea.draft_scores = draft_scores(idea, block)
        idea.score_model = "dry-run" if llm.dry_run() else llm.TASK_MODELS["score"]
        store.save_idea(idea)
        total = idea.draft_scores.weighted_total(store.load_weights())
        print(f"  {idea.id}  weighted={total}  {idea.title[:60]}")
        n += 1
    return n


def review_interactive() -> int:
    """Human accepts/adjusts each drafted score. Deltas -> calibration log."""
    import typer

    weights = store.load_weights()
    reviewed = 0
    for idea in store.iter_ideas():
        if idea.draft_scores is None or idea.final_scores is not None:
            continue
        d = idea.draft_scores
        print(f"\n=== {idea.id}: {idea.title}")
        print(f"    {idea.summary[:300]}")
        finals = {}
        for f in FACTORS:
            drafted = getattr(d, f)
            just = d.justifications.get(f, "")
            val = typer.prompt(f"  {f} (draft {drafted} - {just[:100]})", default=drafted, type=int)
            finals[f] = max(1, min(5, val))
            if finals[f] != drafted:
                store.append_jsonl(paths.calibration_dir() / "score_adjustments.jsonl", {
                    "idea_id": idea.id, "factor": f, "draft": drafted, "final": finals[f],
                    "justification": just,
                })
        idea.final_scores = FactorScores(**finals, justifications=d.justifications)
        store.save_idea(idea)
        print(f"    final weighted: {idea.final_scores.weighted_total(weights)}")
        reviewed += 1
    return reviewed
