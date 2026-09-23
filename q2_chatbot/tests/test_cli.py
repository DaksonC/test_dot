"""Testes do loop de terminal com entradas simuladas e LLM falso."""

import httpx
import openai
import pytest
from langchain_core.runnables import RunnableLambda

from chatbot.cli import FatalChatError, run_chat
from chatbot.chain import build_chain
from tests.conftest import make_fake_llm


class Terminal:
    """Simula o terminal: entrega entradas roteirizadas e acumula a saída."""

    def __init__(self, *inputs: str) -> None:
        self._inputs = iter(inputs)
        self.output = ""

    def input(self, _prompt: str) -> str:
        try:
            return next(self._inputs)
        except StopIteration:
            raise EOFError from None

    def write(self, text: str) -> None:
        self.output += text


def _api_error(cls, status: int):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return cls("erro simulado", response=httpx.Response(status, request=request), body=None)


def _failing_chain(exc: Exception):
    def boom(_):
        raise exc
    return RunnableLambda(boom)


def test_answers_question_and_exits(chain, store):
    term = Terminal("Como criar uma lista em Python?", "/sair")

    run_chat(chain, store, input_fn=term.input, write=term.write)

    assert "Tutor: Use colchetes: `numeros = [1, 2, 3]`." in term.output
    assert term.output.endswith("Até mais!\n")


def test_empty_input_is_ignored(chain, store, fake_llm):
    term = Terminal("", "   ", "/sair")

    run_chat(chain, store, input_fn=term.input, write=term.write)

    assert fake_llm.calls == []


def test_clear_command_resets_history(chain, store, fake_llm):
    term = Terminal("Pergunta 1", "/limpar", "Pergunta 2", "/sair")

    run_chat(chain, store, session_id="s", input_fn=term.input, write=term.write)

    assert "Histórico apagado." in term.output
    assert len(fake_llm.calls[1]) == 2  # system + pergunta, sem o turno anterior


def test_eof_exits_gracefully(chain, store):
    term = Terminal()  # sem entradas: simula Ctrl+D

    run_chat(chain, store, input_fn=term.input, write=term.write)

    assert "Até mais!" in term.output


def test_rate_limit_keeps_loop_running(store):
    term = Terminal("pergunta", "/sair")
    chain = _failing_chain(_api_error(openai.RateLimitError, 429))

    run_chat(chain, store, input_fn=term.input, write=term.write)

    assert "Limite de requisições" in term.output
    assert term.output.endswith("Até mais!\n")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (_api_error(openai.AuthenticationError, 401), "OPENAI_API_KEY"),
        (_api_error(openai.NotFoundError, 404), "OPENAI_MODEL"),
    ],
)
def test_fatal_errors_stop_the_loop(store, error, message):
    term = Terminal("pergunta", "/sair")

    with pytest.raises(FatalChatError, match=message):
        run_chat(_failing_chain(error), store, input_fn=term.input, write=term.write)


def test_failed_turn_is_not_saved_in_history(store):
    # Se o LLM falha, a pergunta não deve ficar "órfã" no histórico.
    llm = make_fake_llm()  # sem respostas: a chamada falha
    chain = build_chain(llm, store)
    term = Terminal("pergunta")

    with pytest.raises(Exception):
        run_chat(chain, store, session_id="s", input_fn=term.input, write=term.write)

    assert store.get("s").messages == []
