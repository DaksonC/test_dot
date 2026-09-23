"""Montagem da chain de conversa: prompt de tutor + LLM + memória por sessão."""

import warnings
from operator import itemgetter

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from chatbot.config import Settings

# RunnableWithMessageHistory e InMemoryChatMessageHistory seguem funcionais, mas
# o LangChain 1.x os marca como deprecated em favor da persistência do LangGraph
# (remoção prevista para a 2.0; por isso langchain-core está fixado em 1.x).
# Silenciamos só esses dois avisos para não poluir o terminal do usuário.
# Ver "Decisões técnicas" no README.
warnings.filterwarnings(
    "ignore",
    message=r".*(RunnableWithMessageHistory|InMemoryChatMessageHistory).*deprecated",
    category=DeprecationWarning,
)

# Observação: o texto passa pelo ChatPromptTemplate, então chaves literais
# precisariam ser escapadas; por isso o prompt não usa chaves.
SYSTEM_PROMPT = """\
Você é um tutor paciente e experiente de programação em Python.

Como responder:
- Responda sempre em português do Brasil.
- Explique o conceito de forma clara e detalhada, do básico ao intermediário.
- Inclua exemplos de código curtos e executáveis, em blocos de código Python, com comentários.
- Quando fizer sentido, mostre variações, erros comuns e boas práticas (PEP 8).
- Se a pergunta for ambígua, assuma a interpretação mais comum e diga qual assumiu.

Escopo:
- Você responde apenas sobre Python e programação em geral.
- Para assuntos fora desse escopo, recuse educadamente e sugira uma pergunta sobre Python.
"""


def build_prompt() -> ChatPromptTemplate:
    """Prompt com instrução de sistema, histórico da conversa e a pergunta atual."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]
    )


class SessionStore:
    """Guarda o histórico de cada conversa em memória, indexado por session_id.

    Em produção isso iria para Redis/banco (há implementações prontas de
    BaseChatMessageHistory), para sobreviver a reinícios e escalar horizontalmente.
    """

    def __init__(self) -> None:
        self._histories: dict[str, InMemoryChatMessageHistory] = {}

    def get(self, session_id: str) -> InMemoryChatMessageHistory:
        return self._histories.setdefault(session_id, InMemoryChatMessageHistory())

    def clear(self, session_id: str) -> None:
        self._histories.pop(session_id, None)


def build_llm(settings: Settings, max_retries: int | None = None) -> ChatOpenAI:
    """Cria o cliente do modelo da OpenAI a partir das configurações.

    max_retries=None mantém o padrão do SDK da OpenAI.
    """
    kwargs: dict = {}
    if settings.temperature is not None:
        kwargs["temperature"] = settings.temperature
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    return ChatOpenAI(model=settings.model, api_key=settings.openai_api_key, **kwargs)


def build_chain(
    llm: BaseChatModel,
    store: SessionStore,
    max_history_messages: int = 20,
) -> RunnableWithMessageHistory:
    """Monta a chain com memória.

    Fluxo: {question, history} -> recorta o histórico -> prompt -> LLM -> texto.

    O RunnableWithMessageHistory busca o histórico da sessão (via
    config["configurable"]["session_id"]), injeta em "history" e, ao final,
    grava a pergunta e a resposta. Se a chamada falhar, nada é gravado.
    """
    # Envia ao modelo só as últimas N mensagens, para limitar custo e não
    # estourar a janela de contexto. token_counter=len conta mensagens, não
    # tokens: simples e previsível. start_on="human" evita começar o recorte
    # com uma resposta solta do assistente.
    trimmer = trim_messages(
        max_tokens=max_history_messages,
        token_counter=len,
        strategy="last",
        start_on="human",
    )

    chain = (
        RunnablePassthrough.assign(history=itemgetter("history") | trimmer)
        | build_prompt()
        | llm
        | StrOutputParser()
    )

    return RunnableWithMessageHistory(
        chain,
        store.get,
        input_messages_key="question",
        history_messages_key="history",
    )
