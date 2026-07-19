"""Single LLM wrapper. Every CPI model call goes through here.

- Per-task model selection (Haiku for volume tasks, Opus for judgment tasks)
- Prompt templates loaded from prompts/<task>.md (editable without code changes)
- Token usage logged to data/llm_usage.jsonl
- CPI_DRY_RUN=1 returns deterministic canned outputs (tests / keyless runs)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from string import Template

from . import paths

TASK_MODELS = {
    "summarize": "claude-haiku-4-5",
    "triage": "claude-haiku-4-5",
    "score": "claude-opus-4-8",
    "brief": "claude-opus-4-8",
    "calibrate": "claude-opus-4-8",
}

MAX_TOKENS = {
    "summarize": 1024,
    "triage": 1024,
    "score": 4096,
    "brief": 8192,
    "calibrate": 4096,
}

_client = None


def dry_run() -> bool:
    return os.environ.get("CPI_DRY_RUN", "") == "1"


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def load_prompt(task: str, **vars) -> str:
    path = paths.prompts_dir() / f"{task}.md"
    template = Template(path.read_text(encoding="utf-8"))
    # Few-shot calibration examples (written by Stage 6) are injected when present.
    fewshots = paths.calibration_dir() / f"fewshots_{task}.md"
    vars.setdefault("calibration_examples", fewshots.read_text(encoding="utf-8") if fewshots.exists() else "(none yet)")
    return template.safe_substitute(**vars)


def _log_usage(task: str, model: str, usage) -> None:
    paths.data_dir().mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "model": model,
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }
    with open(paths.llm_usage_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def complete(task: str, **vars) -> str:
    """Free-text completion for `task` using its prompt template."""
    if dry_run():
        return _canned_text(task, vars)
    prompt = load_prompt(task, **vars)
    model = TASK_MODELS[task]
    client = _get_client()
    kwargs = dict(model=model, max_tokens=MAX_TOKENS[task],
                  messages=[{"role": "user", "content": prompt}])
    if model.startswith("claude-opus"):
        kwargs["thinking"] = {"type": "adaptive"}
    with client.messages.stream(**kwargs) as stream:
        response = stream.get_final_message()
    _log_usage(task, model, response.usage)
    return next((b.text for b in response.content if b.type == "text"), "")


def complete_json(task: str, schema: dict, **vars) -> dict:
    """Schema-constrained JSON completion (structured outputs)."""
    if dry_run():
        return _canned_json(task, vars)
    prompt = load_prompt(task, **vars)
    model = TASK_MODELS[task]
    client = _get_client()
    kwargs = dict(
        model=model,
        max_tokens=MAX_TOKENS[task],
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if model.startswith("claude-opus"):
        kwargs["thinking"] = {"type": "adaptive"}
    response = client.messages.create(**kwargs)
    _log_usage(task, model, response.usage)
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ── Dry-run canned outputs ─────────────────────────────────────────────────

def _canned_text(task: str, vars: dict) -> str:
    if task == "summarize":
        raw = str(vars.get("raw_excerpt", ""))[:300]
        return json.dumps({"summary": raw or "Dry-run summary.",
                           "claimed_significance": "Dry-run significance."})
    if task == "brief":
        return (
            "## The idea\nDry-run idea statement.\n\n"
            "## The signal\nDry-run signal summary with sources.\n\n"
            "## Why now\nDry-run timing argument.\n\n"
            "## Cost of inaction\nDry-run cost.\n\n"
            "## Pros\n- Pro one (impact)\n- Pro two (strategic fit)\n- Pro three (timing)\n\n"
            "## Cons & risks\n- Con one stated plainly\n- Con two stated plainly\n- Con three stated plainly\n\n"
            "## Suggested next step\nA two-day probe."
        )
    return "Dry-run output."


def _canned_json(task: str, vars: dict) -> dict:
    if task == "triage":
        return {"disposition": "advance", "rationale": "Dry-run: matches a watch theme.",
                "confidence": 0.5, "re_review_trigger": None}
    if task == "score":
        return {
            "impact": 3, "strategic_fit": 3, "effort": 3, "timing": 3, "confidence": 3,
            "justifications": {f: "Dry-run justification." for f in
                               ("impact", "strategic_fit", "effort", "timing", "confidence")},
        }
    if task == "summarize":
        return {"summary": str(vars.get("raw_excerpt", ""))[:300] or "Dry-run summary.",
                "claimed_significance": "Dry-run significance."}
    return {}
