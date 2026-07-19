"""PCM loading, validation, and prompt-block rendering."""

from __future__ import annotations

from pathlib import Path

import yaml

from . import paths
from .models import PCM


def load(path: Path | None = None) -> PCM:
    pcm_path = path or (paths.context_dir() / "pcm.yaml")
    with open(pcm_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return PCM.model_validate(raw)


def render_prompt_block(pcm: PCM) -> str:
    """Render the PCM into the compact block injected into every LLM prompt."""
    lines: list[str] = [f"# Product Context Model — {pcm.product_name} (v{pcm.version})", ""]

    lines.append("## Capabilities today")
    for c in pcm.capability_map:
        lines.append(f"- {c.name} [{c.maturity}]: {c.description}")

    lines.append("\n## Users & jobs")
    for k, v in pcm.user_and_job_model.items():
        lines.append(f"- {k}: {_flat(v)}")

    sf = pcm.strategy_frame
    lines.append("\n## Strategy")
    lines.append("- Where we intend to win: " + "; ".join(sf.where_we_win))
    lines.append("- NON-GOALS (signals pulling toward these should score poorly): " + "; ".join(sf.non_goals))
    if sf.roadmap_themes:
        lines.append("- Current roadmap themes: " + "; ".join(sf.roadmap_themes))

    lines.append("\n## Technical posture")
    for k, v in pcm.technical_posture.items():
        lines.append(f"- {k}: {_flat(v)}")

    lines.append("\n## Competitive set")
    for comp in pcm.competitive_set:
        name = comp.get("name", "?")
        direction = comp.get("direction", "")
        lines.append(f"- {name}: {direction}")

    lines.append("\n## Watch themes (declared strategically interesting)")
    for t in pcm.watch_themes:
        lines.append(f"- {t.name}: {t.rationale} (keywords: {', '.join(t.keywords)})")

    return "\n".join(lines)


def _flat(v) -> str:
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}={_flat(x)}" for k, x in v.items())
    return str(v)


def append_changelog(entry: str) -> None:
    from datetime import date

    path = paths.context_dir() / "pcm_changelog.md"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- {date.today().isoformat()}: {entry}")
