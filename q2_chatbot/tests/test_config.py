"""Testes do carregamento de configuração (sem ler o .env real)."""

import pytest

from chatbot.config import DEFAULT_MODEL, ConfigError, load_settings


def test_missing_api_key_raises():
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_settings({})


def test_blank_api_key_is_treated_as_missing():
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_settings({"OPENAI_API_KEY": "   "})


def test_defaults():
    settings = load_settings({"OPENAI_API_KEY": "sk-teste"})

    assert settings.model == DEFAULT_MODEL
    assert settings.temperature is None
    assert settings.langsmith_tracing is False


def test_custom_model_and_temperature():
    settings = load_settings(
        {"OPENAI_API_KEY": "sk-teste", "OPENAI_MODEL": "gpt-4o", "OPENAI_TEMPERATURE": "0.3"}
    )

    assert settings.model == "gpt-4o"
    assert settings.temperature == 0.3


@pytest.mark.parametrize("value", ["abc", "3", "-1"])
def test_invalid_temperature_raises(value):
    with pytest.raises(ConfigError, match="OPENAI_TEMPERATURE"):
        load_settings({"OPENAI_API_KEY": "sk-teste", "OPENAI_TEMPERATURE": value})


def test_tracing_enabled_with_key():
    settings = load_settings(
        {
            "OPENAI_API_KEY": "sk-teste",
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_API_KEY": "lsv2-teste",
            "LANGSMITH_PROJECT": "tutor-python",
        }
    )

    assert settings.langsmith_tracing is True
    assert settings.langsmith_project == "tutor-python"


def test_tracing_without_langsmith_key_raises():
    with pytest.raises(ConfigError, match="LANGSMITH_API_KEY"):
        load_settings({"OPENAI_API_KEY": "sk-teste", "LANGSMITH_TRACING": "true"})
