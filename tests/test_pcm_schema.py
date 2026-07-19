"""PCM loading, validation, and prompt-block rendering."""

import pytest
from pydantic import ValidationError

from cpi import pcm as pcm_mod
from cpi.models import PCM


def test_default_pcm_loads(cpi_home):
    p = pcm_mod.load()
    assert p.product_name == "ExampleProduct"
    assert 5 <= len(p.watch_themes) <= 10
    assert p.strategy_frame.non_goals  # non-goals are mandatory in spirit


def test_template_pcm_loads(cpi_home):
    p = pcm_mod.load(cpi_home / "context" / "pcm.template.yaml")
    assert p.product_name == "ExampleProduct"


def test_prompt_block_renders(cpi_home):
    p = pcm_mod.load()
    block = pcm_mod.render_prompt_block(p)
    assert "NON-GOALS" in block
    assert "Watch themes" in block
    for t in p.watch_themes:
        assert t.name in block


def test_invalid_pcm_rejected():
    with pytest.raises(ValidationError):
        PCM.model_validate({"product_name": "X", "capability_map": [],
                            "user_and_job_model": {}, "strategy_frame": {"where_we_win": [], "non_goals": []},
                            "technical_posture": {}, "competitive_set": [],
                            "watch_themes": []})  # zero watch themes -> invalid
