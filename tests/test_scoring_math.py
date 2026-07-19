"""Weighted-total math and weights validation."""

import pytest
import yaml

from cpi import store
from cpi.models import FactorScores


def test_weighted_total(cpi_home):
    weights = store.load_weights()
    s = FactorScores(impact=5, strategic_fit=4, effort=3, timing=2, confidence=1)
    expected = 5 * 0.30 + 4 * 0.25 + 3 * 0.20 + 2 * 0.15 + 1 * 0.10
    assert s.weighted_total(weights) == round(expected, 3)


def test_uniform_scores(cpi_home):
    weights = store.load_weights()
    s = FactorScores(impact=3, strategic_fit=3, effort=3, timing=3, confidence=3)
    assert s.weighted_total(weights) == 3.0


def test_weights_must_sum_to_one(cpi_home):
    bad = {"impact": 0.5, "strategic_fit": 0.25, "effort": 0.20, "timing": 0.15, "confidence": 0.10}
    (cpi_home / "config" / "weights.yaml").write_text(yaml.dump(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="sum to 1.0"):
        store.load_weights()


def test_score_bounds():
    with pytest.raises(Exception):
        FactorScores(impact=6, strategic_fit=3, effort=3, timing=3, confidence=3)
