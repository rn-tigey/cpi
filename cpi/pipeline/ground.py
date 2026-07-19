"""Stage 1b - Ground: translate the PCM into per-source search criteria.

The PCM states themes strategically; each channel (arXiv, HN, trade press)
uses its own vocabulary. A standard set (competitor names) is derived
mechanically; the per-theme translation is an LLM judgment task. The output
(config/search.yaml) is human-reviewable and editable - scanners fall back
to the raw PCM keywords when it is absent.
"""

from __future__ import annotations

import re

from .. import llm, store
from .. import pcm as pcm_mod
from ..models import SearchCriteria, ThemeSearch

GROUND_SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "arxiv_queries": {"type": "array", "items": {"type": "string"}},
                    "hn_keywords": {"type": "array", "items": {"type": "string"}},
                    "press_keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["theme", "arxiv_queries", "hn_keywords", "press_keywords"],
            },
        }
    },
    "required": ["themes"],
}


def standard_keywords(pcm) -> list[str]:
    """Mechanical always-watch set: competitor/adjacent names from the PCM."""
    out: list[str] = []
    for comp in pcm.competitive_set:
        name = re.sub(r"\(.*?\)", "", str(comp.get("name", ""))).strip()
        for part in name.split("/"):
            part = part.strip()
            # keep short brand-like names; long fragments are descriptions, not queries
            if part and len(part.split()) <= 3 and part not in out:
                out.append(part)
    return out


def run(force: bool = False) -> str:
    if store.load_search_criteria() is not None and not force:
        raise SystemExit("config/search.yaml already exists. Re-run with --force to regenerate.")
    p = pcm_mod.load()
    names = [t.name for t in p.watch_themes]
    data = llm.complete_json(
        "ground", GROUND_SCHEMA,
        pcm_block=pcm_mod.render_prompt_block(p),
        theme_names="\n".join(names),
    )

    themes: list[ThemeSearch] = []
    for entry in data.get("themes", []):
        if entry["theme"] not in names:
            print(f"  [ground] dropping unknown theme from LLM output: {entry['theme']!r}")
            continue
        themes.append(ThemeSearch(**entry))
    covered = {t.theme for t in themes}
    for name in names:
        if name not in covered:
            # never leave a theme searchless - fall back to its PCM keywords
            src = next(t for t in p.watch_themes if t.name == name)
            print(f"  [ground] LLM skipped theme {name!r}; using its PCM keywords")
            themes.append(ThemeSearch(theme=name, arxiv_queries=src.keywords,
                                      hn_keywords=src.keywords, press_keywords=src.keywords))

    criteria = SearchCriteria(
        generated_from_pcm_version=p.version,
        standard_keywords=standard_keywords(p),
        themes=themes,
    )
    path = store.save_search_criteria(criteria)
    pcm_mod.append_changelog(f"search criteria (config/search.yaml) generated from PCM v{p.version}")
    for t in themes:
        print(f"  {t.theme}: arxiv={len(t.arxiv_queries)} hn={len(t.hn_keywords)} press={len(t.press_keywords)}")
    return str(path)
