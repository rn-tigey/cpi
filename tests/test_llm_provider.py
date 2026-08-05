"""Provider selection - Anthropic by default, OpenAI opt-in."""

import pytest

from cpi import llm


def test_default_is_anthropic(monkeypatch):
    monkeypatch.delenv("CPI_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.provider() == "anthropic"
    assert llm.model_for("triage") == llm.TASK_MODELS["triage"]


def test_openai_auto_selected_when_it_is_the_only_key(monkeypatch):
    monkeypatch.delenv("CPI_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.provider() == "openai"
    assert llm.model_for("score") == llm.TASK_MODELS_OPENAI["score"]


def test_anthropic_key_keeps_the_default_even_alongside_openai_key(monkeypatch):
    monkeypatch.delenv("CPI_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert llm.provider() == "anthropic"


def test_cpi_provider_env_var_overrides_key_detection(monkeypatch):
    monkeypatch.setenv("CPI_PROVIDER", "openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm.provider() == "openai"


def test_invalid_provider_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("CPI_PROVIDER", "gemini")
    with pytest.raises(SystemExit):
        llm.provider()


def test_both_task_maps_cover_the_same_tasks():
    assert set(llm.TASK_MODELS) == set(llm.TASK_MODELS_OPENAI)
