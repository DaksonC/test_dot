"""Carregamento e validação da configuração a partir de variáveis de ambiente.

As variáveis podem vir do ambiente ou de um arquivo .env (python-dotenv).
Nenhuma chave é escrita no código.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

# Modelo padrão: otimizado para custo, suficiente para explicações didáticas.
# Pode ser trocado com OPENAI_MODEL (ex.: gpt-5.6-terra, gpt-4o).
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_MAX_HISTORY_MESSAGES = 20

_TRUTHY = {"1", "true", "yes", "on"}


class ConfigError(Exception):
    """Configuração ausente ou inválida; a mensagem é exibida ao usuário."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    model: str = DEFAULT_MODEL
    # None = não enviar e usar o padrão do modelo. Modelos de raciocínio
    # (família GPT-5) podem rejeitar valores diferentes do padrão.
    temperature: float | None = None
    max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES
    langsmith_tracing: bool = False
    langsmith_project: str | None = None


def _get(env: Mapping[str, str], key: str) -> str | None:
    """Lê a variável tratando string vazia (comum no .env.example) como ausente."""
    value = env.get(key, "").strip()
    return value or None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Monta as configurações validadas.

    Sem `env`, carrega o .env (procurando a partir desta pasta para cima) e
    usa os.environ. Os testes passam um dicionário para não depender do ambiente.
    """
    if env is None:
        # override=False: variáveis já exportadas no shell têm prioridade sobre o .env.
        load_dotenv(override=False)
        env = os.environ

    api_key = _get(env, "OPENAI_API_KEY")
    if api_key is None:
        raise ConfigError(
            "OPENAI_API_KEY não definida. Copie .env.example para .env e preencha a chave."
        )

    temperature_raw = _get(env, "OPENAI_TEMPERATURE")
    try:
        temperature = float(temperature_raw) if temperature_raw is not None else None
    except ValueError:
        raise ConfigError(f"OPENAI_TEMPERATURE inválida: {temperature_raw!r}") from None
    if temperature is not None and not 0 <= temperature <= 2:
        raise ConfigError("OPENAI_TEMPERATURE deve estar entre 0 e 2.")

    history_raw = _get(env, "CHAT_MAX_HISTORY_MESSAGES")
    try:
        max_history = int(history_raw) if history_raw is not None else DEFAULT_MAX_HISTORY_MESSAGES
    except ValueError:
        raise ConfigError(f"CHAT_MAX_HISTORY_MESSAGES inválida: {history_raw!r}") from None
    if max_history < 0:
        raise ConfigError("CHAT_MAX_HISTORY_MESSAGES não pode ser negativa.")

    # O LangChain ativa o tracing sozinho ao ler LANGSMITH_TRACING/LANGSMITH_API_KEY
    # do ambiente. Aqui só validamos a combinação, para falhar cedo com uma
    # mensagem clara em vez de erros de autenticação no meio da conversa.
    tracing = (_get(env, "LANGSMITH_TRACING") or "").lower() in _TRUTHY
    if tracing and _get(env, "LANGSMITH_API_KEY") is None:
        raise ConfigError("LANGSMITH_TRACING=true exige LANGSMITH_API_KEY.")

    return Settings(
        openai_api_key=api_key,
        model=_get(env, "OPENAI_MODEL") or DEFAULT_MODEL,
        temperature=temperature,
        max_history_messages=max_history,
        langsmith_tracing=tracing,
        langsmith_project=_get(env, "LANGSMITH_PROJECT"),
    )
