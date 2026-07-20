"""Stage 0 - Draft a PCM from existing artifacts (PRDs, docs, a git repo).

The machine does the exhaustive reading of what the team already wrote; the
human answers only the open questions the artifacts could not - above all
non-goals, which documents almost never state. The output is a DRAFT: it is
written with a review header and must be edited before it is trusted.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import yaml

from .. import llm, paths
from .. import pcm as pcm_mod
from ..models import PCM

DOC_EXTS = {".md", ".markdown", ".txt", ".rst", ".yaml", ".yml"}
MANIFEST_NAMES = {"pyproject.toml", "package.json", "requirements.txt", "Cargo.toml",
                  "go.mod", "pom.xml", "build.gradle", "Gemfile", "composer.json"}
PER_FILE_CAP = 9000     # chars per artifact
TOTAL_CAP = 90000       # chars across all artifacts
GIT_LOG_LINES = 30

_STR_ARRAY = {"type": "array", "items": {"type": "string"}}

DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "product_name": {"type": "string"},
        "capability_map": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"name": {"type": "string"}, "description": {"type": "string"},
                           "maturity": {"type": "string",
                                        "enum": ["nascent", "maturing", "mature"]}},
            "required": ["name", "description", "maturity"]}},
        "user_and_job_model": {
            "type": "object", "additionalProperties": False,
            "properties": {"segments": _STR_ARRAY, "jobs_to_be_done": _STR_ARRAY,
                           "top_unmet_needs": _STR_ARRAY},
            "required": ["segments", "jobs_to_be_done", "top_unmet_needs"]},
        "strategy_frame": {
            "type": "object", "additionalProperties": False,
            "properties": {"where_we_win": _STR_ARRAY, "non_goals": _STR_ARRAY,
                           "roadmap_themes": _STR_ARRAY},
            "required": ["where_we_win", "non_goals", "roadmap_themes"]},
        "technical_posture": {
            "type": "object", "additionalProperties": False,
            "properties": {"stack": {"type": "string"}, "dependencies": _STR_ARRAY,
                           "constraints": _STR_ARRAY},
            "required": ["stack", "dependencies", "constraints"]},
        "competitive_set": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"name": {"type": "string"},
                           "type": {"type": "string",
                                    "enum": ["direct", "adjacent", "substitute"]},
                           "direction": {"type": "string"}},
            "required": ["name", "type", "direction"]}},
        "watch_themes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"name": {"type": "string"}, "rationale": {"type": "string"},
                           "arxiv_categories": _STR_ARRAY, "keywords": _STR_ARRAY},
            "required": ["name", "rationale", "arxiv_categories", "keywords"]}},
        "open_questions": _STR_ARRAY,
        "low_confidence": _STR_ARRAY,
    },
    "required": ["product_name", "capability_map", "user_and_job_model", "strategy_frame",
                 "technical_posture", "competitive_set", "watch_themes",
                 "open_questions", "low_confidence"],
}


# ── artifact gathering ─────────────────────────────────────────────────────

def _read_capped(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:PER_FILE_CAP]
    except OSError:
        return ""


def gather_docs(folders: list[Path]) -> list[tuple[str, str]]:
    """(label, text) per readable doc file, skipping hidden/vendored dirs."""
    out: list[tuple[str, str]] = []
    for folder in folders:
        if folder.is_file():
            out.append((folder.name, _read_capped(folder)))
            continue
        for p in sorted(folder.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in DOC_EXTS:
                continue
            rel = p.relative_to(folder)
            # judge hidden/vendored dirs INSIDE the folder only - the folder
            # itself may legitimately live under a dotted path
            if any(part.startswith(".") or part in ("node_modules", "venv")
                   for part in rel.parts):
                continue
            out.append((str(rel), _read_capped(p)))
    return out


def gather_repo(repo: Path) -> list[tuple[str, str]]:
    """README/docs/changelog/manifests, a shallow tree, and recent git subjects."""
    out: list[tuple[str, str]] = []
    for pattern in ("README*", "CHANGELOG*"):
        for p in sorted(repo.glob(pattern)):
            if p.is_file():
                out.append((p.name, _read_capped(p)))
    docs = repo / "docs"
    if docs.is_dir():
        out.extend((f"docs/{p.name}", _read_capped(p))
                   for p in sorted(docs.rglob("*")) if p.suffix.lower() in DOC_EXTS)
    for name in sorted(MANIFEST_NAMES):
        p = repo / name
        if p.is_file():
            out.append((name, _read_capped(p)))
    tree = [str(p.relative_to(repo)) for p in sorted(repo.glob("*/"))
            if not p.name.startswith(".")]
    out.append(("repository top-level folders", "\n".join(tree)))
    try:
        log = subprocess.run(["git", "-C", str(repo), "log", "--oneline",
                              f"-{GIT_LOG_LINES}"],
                             capture_output=True, text=True, timeout=15)
        if log.returncode == 0 and log.stdout.strip():
            out.append(("recent git commit subjects", log.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return out


def artifacts_block(parts: list[tuple[str, str]]) -> str:
    blocks, used = [], 0
    for label, text in parts:
        text = (text or "").strip()
        if not text:
            continue
        take = text[: max(0, TOTAL_CAP - used)]
        if not take:
            blocks.append(f"(further artifacts truncated: {label} ...)")
            break
        blocks.append(f"### {label}\n{take}")
        used += len(take)
    return "\n\n".join(blocks)


# ── draft rendering ────────────────────────────────────────────────────────

def render_draft(data: dict) -> str:
    questions = data.pop("open_questions", [])
    low_conf = data.pop("low_confidence", [])
    body = yaml.safe_dump({
        "product_name": data["product_name"],
        "version": "draft-1",
        "capability_map": data["capability_map"],
        "user_and_job_model": data["user_and_job_model"],
        "strategy_frame": data["strategy_frame"],
        "technical_posture": data["technical_posture"],
        "competitive_set": data["competitive_set"],
        "watch_themes": data["watch_themes"],
    }, sort_keys=False, allow_unicode=True, width=100)
    header = ["# ══════════════════════════════════════════════════════════════════",
              "# DRAFT PCM - generated by `cpi draft-pcm` on " + date.today().isoformat(),
              "# Review every entry before running the pipeline. In particular:",
              "#"]
    header += [f"# OPEN QUESTION {i}: {q}" for i, q in enumerate(questions, 1)]
    if low_conf:
        header.append("#")
        header.append("# LOW-CONFIDENCE entries (weak evidence - confirm or delete):")
        header += [f"#   - {item}" for item in low_conf]
    header += ["#",
               "# When done: bump `version` to \"1\", log it in pcm_changelog.md,",
               "# then run `cpi ground`.",
               "# ══════════════════════════════════════════════════════════════════"]
    return "\n".join(header) + "\n" + body


def run(docs: list[Path], repo: Path | None, force: bool = False) -> str:
    target = paths.context_dir() / "pcm.yaml"
    existing_is_template = False
    if target.exists():
        try:
            existing_is_template = pcm_mod.load().product_name == "ExampleProduct"
        except Exception:
            existing_is_template = False
        if not force and not existing_is_template:
            raise SystemExit(f"{target} already exists and is not the seed template. "
                             "Re-run with --force to overwrite.")

    parts: list[tuple[str, str]] = gather_docs(docs)
    if repo is not None:
        parts += gather_repo(repo)
    if not any(text.strip() for _, text in parts):
        raise SystemExit("No readable artifacts found. Pass --docs folders (.md/.txt/...) "
                         "and/or --repo <path>.")

    data = llm.complete_json("draft_pcm", DRAFT_SCHEMA,
                             artifacts_block=artifacts_block(parts))
    questions = list(data.get("open_questions", []))

    draft_text = render_draft(dict(data))
    PCM.model_validate(yaml.safe_load(draft_text))  # never write an unloadable PCM

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(draft_text, encoding="utf-8")
    pcm_mod.append_changelog(
        f"DRAFT PCM generated by `cpi draft-pcm` from {len(parts)} artifact(s) - pending review")

    print(f"  drafted from {len(parts)} artifact(s)")
    for i, q in enumerate(questions, 1):
        print(f"  OPEN QUESTION {i}: {q}")
    return str(target)
