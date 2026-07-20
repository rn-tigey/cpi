"""Stage 0 - draft-pcm: artifact gathering, draft rendering, guardrails."""

import pytest
import yaml

from cpi import pcm as pcm_mod
from cpi.pipeline import draft_pcm


def _docs_folder(tmp_path):
    d = tmp_path / "prds"
    d.mkdir()
    (d / "vision.md").write_text("# Vision\nWe help small teams tame their inboxes.",
                                 encoding="utf-8")
    (d / "notes.txt").write_text("Support asks for calendar-aware priorities.",
                                 encoding="utf-8")
    (d / "binary.png").write_bytes(b"\x89PNG")  # ignored: not a doc extension
    return d


def test_gather_docs_reads_only_doc_files(tmp_path):
    parts = draft_pcm.gather_docs([_docs_folder(tmp_path)])
    labels = [label for label, _ in parts]
    assert "vision.md" in labels and "notes.txt" in labels
    assert not any("png" in label for label in labels)


def test_artifacts_block_caps_total_size():
    parts = [("big1.md", "x" * 80000), ("big2.md", "y" * 80000)]
    block = draft_pcm.artifacts_block(parts)
    assert len(block) < draft_pcm.TOTAL_CAP + 2000
    # second file only gets the remaining budget
    assert block.count("y") == draft_pcm.TOTAL_CAP - 80000


def test_draft_writes_loadable_pcm_with_questions(cpi_home, tmp_path):
    path = draft_pcm.run(docs=[_docs_folder(tmp_path)], repo=None, force=True)
    text = open(path, encoding="utf-8").read()
    assert "DRAFT PCM" in text
    assert "OPEN QUESTION 1:" in text
    p = pcm_mod.load()  # the draft must be a valid, loadable PCM
    assert p.product_name == "DraftedProduct"
    assert p.version == "draft-1"
    assert 5 <= len(p.watch_themes)


def test_draft_overwrites_seed_template_but_not_real_pcm(cpi_home, tmp_path):
    docs = [_docs_folder(tmp_path)]
    # the seeded home pcm.yaml is the ExampleProduct template - overwrite allowed
    draft_pcm.run(docs=docs, repo=None)
    # now the file is a real (drafted) PCM - a second run must refuse without --force
    with pytest.raises(SystemExit):
        draft_pcm.run(docs=docs, repo=None)
    draft_pcm.run(docs=docs, repo=None, force=True)


def test_draft_requires_some_artifacts(cpi_home, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SystemExit):
        draft_pcm.run(docs=[empty], repo=None, force=True)


def test_render_draft_yaml_survives_roundtrip():
    from cpi.llm import _canned_json
    data = _canned_json("draft_pcm", {})
    text = draft_pcm.render_draft(dict(data))
    loaded = yaml.safe_load(text)
    assert loaded["product_name"] == "DraftedProduct"
    assert loaded["strategy_frame"]["non_goals"] == ["Dry-run non-goal"]
