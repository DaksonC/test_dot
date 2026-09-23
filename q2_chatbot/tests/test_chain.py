"""Testes da chain: prompt de sistema, memória por sessão e recorte do histórico."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from chatbot.chain import SYSTEM_PROMPT, build_chain
from tests.conftest import make_fake_llm, session


def test_returns_model_answer_as_text(chain):
    answer = chain.invoke({"question": "Como criar uma lista em Python?"}, config=session())

    assert answer == "Use colchetes: `numeros = [1, 2, 3]`."


def test_sends_system_prompt_and_question(chain, fake_llm):
    chain.invoke({"question": "Como criar uma lista em Python?"}, config=session())

    messages = fake_llm.calls[0]
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == SYSTEM_PROMPT
    assert messages[-1] == HumanMessage(content="Como criar uma lista em Python?")


def test_second_question_receives_previous_turn(chain, fake_llm):
    chain.invoke({"question": "Como criar uma lista em Python?"}, config=session())
    chain.invoke({"question": "E como adiciono itens?"}, config=session())

    second_call = fake_llm.calls[1]
    assert second_call[1:] == [
        HumanMessage(content="Como criar uma lista em Python?"),
        AIMessage(content="Use colchetes: `numeros = [1, 2, 3]`."),
        HumanMessage(content="E como adiciono itens?"),
    ]


def test_history_is_stored_per_session(chain, store):
    chain.invoke({"question": "Pergunta A"}, config=session("a"))
    chain.invoke({"question": "Pergunta B"}, config=session("b"))

    assert [m.content for m in store.get("a").messages][0] == "Pergunta A"
    assert [m.content for m in store.get("b").messages][0] == "Pergunta B"
    assert len(store.get("a").messages) == 2


def test_sessions_do_not_share_memory(chain, fake_llm):
    chain.invoke({"question": "Pergunta A"}, config=session("a"))
    chain.invoke({"question": "Pergunta B"}, config=session("b"))

    # Na sessão "b" o modelo só vê system + a própria pergunta.
    assert len(fake_llm.calls[1]) == 2


def test_clear_removes_history(chain, store, fake_llm):
    chain.invoke({"question": "Pergunta A"}, config=session())
    store.clear("teste")
    chain.invoke({"question": "Pergunta B"}, config=session())

    assert len(fake_llm.calls[1]) == 2


def test_history_sent_to_model_is_trimmed(store):
    llm = make_fake_llm("r1", "r2", "r3")
    chain = build_chain(llm, store, max_history_messages=2)

    for question in ("q1", "q2", "q3"):
        chain.invoke({"question": question}, config=session())

    # Com limite 2, a 3ª chamada leva só o último turno (q2/r2) + a pergunta atual.
    assert [m.content for m in llm.calls[2][1:]] == ["q2", "r2", "q3"]
    # O histórico completo continua guardado; o recorte vale só para o envio.
    assert len(store.get("teste").messages) == 6


def test_stream_yields_full_answer_and_saves_history(chain, store):
    chunks = list(chain.stream({"question": "Como criar uma lista?"}, config=session()))

    assert "".join(chunks) == "Use colchetes: `numeros = [1, 2, 3]`."
    assert len(store.get("teste").messages) == 2
