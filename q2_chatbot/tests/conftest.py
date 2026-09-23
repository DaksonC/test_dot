"""LLM falso para testar a chain sem chamar a API da OpenAI."""

from collections.abc import Iterator
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import Field

from chatbot.chain import SessionStore, build_chain


class RecordingFakeChatModel(GenericFakeChatModel):
    """Modelo falso que devolve respostas pré-definidas e grava o que recebeu.

    `calls[i]` é a lista de mensagens (system + histórico + pergunta) enviada
    na i-ésima chamada, o que permite verificar prompt e memória.
    """

    calls: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any):
        self.calls.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


def make_fake_llm(*answers: str) -> RecordingFakeChatModel:
    responses: Iterator[AIMessage] = iter(AIMessage(content=a) for a in answers)
    return RecordingFakeChatModel(messages=responses)


@pytest.fixture
def store() -> SessionStore:
    return SessionStore()


@pytest.fixture
def fake_llm() -> RecordingFakeChatModel:
    return make_fake_llm(
        "Use colchetes: `numeros = [1, 2, 3]`.",
        "Use `append` para adicionar e `remove` para remover.",
        "Terceira resposta.",
    )


@pytest.fixture
def chain(fake_llm, store):
    return build_chain(fake_llm, store)


def session(session_id: str = "teste") -> dict:
    return {"configurable": {"session_id": session_id}}
