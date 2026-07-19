"""Filesystem layout resolution.

The CPI home directory holds context/, config/, prompts/, data/ and briefs/.
Resolution order:
  1. CPI_HOME environment variable
  2. the current project root (development / in-repo layout)

Pristine copies of every template (PCM template, default configs, prompts)
ship inside the package at cpi/templates/ - `cpi init` seeds new homes from
there, and config/prompt loaders fall back to it when a home lacks a file.
"""

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def home() -> Path:
    env = os.environ.get("CPI_HOME")
    root = Path(env) if env else _PACKAGE_ROOT
    return root


def templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def context_dir() -> Path:
    return home() / "context"


def config_dir() -> Path:
    return home() / "config"


def prompts_dir() -> Path:
    return home() / "prompts"


def data_dir() -> Path:
    return home() / "data"


def briefs_dir() -> Path:
    return home() / "briefs"


def signals_dir() -> Path:
    return data_dir() / "signals"


def triage_dir() -> Path:
    return data_dir() / "triage"


def discards_dir() -> Path:
    return data_dir() / "discards"


def ideas_dir() -> Path:
    return data_dir() / "ideas"


def calibration_dir() -> Path:
    return data_dir() / "calibration"


def decisions_dir() -> Path:
    return data_dir() / "decisions"


def seen_urls_file() -> Path:
    return data_dir() / "seen_urls.txt"


def llm_usage_file() -> Path:
    return data_dir() / "llm_usage.jsonl"


def scan_log_file() -> Path:
    return data_dir() / "scan_log.jsonl"


def ensure_layout() -> None:
    for d in (
        signals_dir(),
        triage_dir(),
        discards_dir(),
        ideas_dir(),
        calibration_dir(),
        decisions_dir(),
        briefs_dir(),
    ):
        d.mkdir(parents=True, exist_ok=True)
