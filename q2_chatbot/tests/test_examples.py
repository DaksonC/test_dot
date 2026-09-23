"""Testes do gerador de exemplos: salvamento incremental e mensagens de erro."""

import httpx
import openai
import pytest
from langchain_core.runnables import RunnableLambda

from chatbot.chain import build_chain
from chatbot.examples import describe_api_error, generate_examples
from tests.conftest import make_fake_llm

QUESTIONS = ["Pergunta 1", "Pergunta 2", "Pergunta 3"]


def _api_error(cls, status: int, code: str | None = None):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    body = {"code": code} if code else None
    return cls("erro simulado", response=httpx.Response(status, request=request), body=body)


def _scripted_chain(*outcomes):
    """Chain que devolve (ou lança) cada item de `outcomes`, em ordem."""
    remaining = iter(outcomes)

    def step(_):
        outcome = next(remaining)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return RunnableLambda(step)


def test_writes_all_answers(tmp_path, store):
    output = tmp_path / "EXEMPLOS.md"
    chain = build_chain(make_fake_llm("R1", "R2", "R3"), store)

    ok = generate_examples(chain, "modelo-x", output, QUESTIONS, log=lambda _: None)

    content = output.read_text(encoding="utf-8")
    assert ok is True
    assert "`modelo-x`" in content
    assert "## 1. Pergunta 1\n\nR1" in content
    assert "## 3. Pergunta 3\n\nR3" in content
    assert "Incompleto" not in content


def test_keeps_partial_answers_when_api_fails(tmp_path):
    output = tmp_path / "EXEMPLOS.md"
    error = _api_error(openai.RateLimitError, 429, "insufficient_quota")
    logs: list[str] = []

    ok = generate_examples(_scripted_chain("R1", "R2", error), "m", output, QUESTIONS, log=logs.append)

    content = output.read_text(encoding="utf-8")
    assert ok is False
    assert "R1" in content and "R2" in content
    assert "**Incompleto:** 2 de 3" in content
    assert any("Erro na pergunta 3" in line and "crédito" in line for line in logs)


def test_does_not_create_file_when_first_question_fails(tmp_path):
    output = tmp_path / "EXEMPLOS.md"
    error = _api_error(openai.AuthenticationError, 401)

    ok = generate_examples(_scripted_chain(error), "m", output, QUESTIONS, log=lambda _: None)

    assert ok is False
    assert not output.exists()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_api_error(openai.RateLimitError, 429, "insufficient_quota"), "Billing"),
        (_api_error(openai.RateLimitError, 429, "rate_limit_exceeded"), "Aguarde"),
        (_api_error(openai.AuthenticationError, 401), "OPENAI_API_KEY"),
        (_api_error(openai.NotFoundError, 404), "OPENAI_MODEL"),
    ],
)
def test_describe_api_error(error, expected):
    assert expected in describe_api_error(error)
