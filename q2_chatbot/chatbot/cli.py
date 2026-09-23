"""Interface de terminal: loop de perguntas e respostas com streaming."""

import sys
from collections.abc import Callable

import openai
from langchain_core.runnables import Runnable

from chatbot.chain import SessionStore, build_chain, build_llm
from chatbot.config import ConfigError, Settings, load_settings

EXIT_COMMANDS = {"/sair", "sair", "exit", "quit"}
CLEAR_COMMAND = "/limpar"
DEFAULT_SESSION_ID = "terminal"

HELP_TEXT = (
    "Pergunte algo sobre Python (ex.: 'Como criar uma lista em Python?').\n"
    f"Comandos: {CLEAR_COMMAND} apaga o histórico | /sair encerra.\n"
)


class FatalChatError(Exception):
    """Erro que não adianta tentar de novo (chave inválida, modelo inexistente)."""


def _stream_answer(chain: Runnable, question: str, session_id: str, write: Callable[[str], None]) -> None:
    """Envia a pergunta e escreve a resposta à medida que os tokens chegam."""
    config = {"configurable": {"session_id": session_id}}
    for chunk in chain.stream({"question": question}, config=config):
        write(chunk)
    write("\n")


def run_chat(
    chain: Runnable,
    store: SessionStore,
    session_id: str = DEFAULT_SESSION_ID,
    input_fn: Callable[[str], str] = input,
    write: Callable[[str], None] = lambda text: print(text, end="", flush=True),
) -> None:
    """Loop principal. input_fn/write são injetáveis para permitir testes sem terminal."""
    write(HELP_TEXT)
    while True:
        try:
            question = input_fn("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D / Ctrl+C encerram sem stack trace.
            write("\nAté mais!\n")
            return

        if not question:
            continue
        if question.lower() in EXIT_COMMANDS:
            write("Até mais!\n")
            return
        if question.lower() == CLEAR_COMMAND:
            store.clear(session_id)
            write("Histórico apagado.\n")
            continue

        write("\nTutor: ")
        try:
            _stream_answer(chain, question, session_id, write)
        except openai.AuthenticationError:
            raise FatalChatError("Chave da OpenAI inválida. Verifique OPENAI_API_KEY.") from None
        except openai.NotFoundError:
            raise FatalChatError(
                "Modelo não encontrado ou sem acesso. Verifique OPENAI_MODEL."
            ) from None
        except openai.RateLimitError:
            write("\n[erro] Limite de requisições ou de créditos atingido. Tente novamente em instantes.\n")
        except (openai.APIConnectionError, openai.APITimeoutError):
            write("\n[erro] Falha de conexão com a OpenAI. Verifique a internet e tente de novo.\n")
        except openai.APIError as exc:
            # Qualquer outro erro da API: informa e mantém a conversa viva.
            write(f"\n[erro] A OpenAI retornou um erro: {exc}\n")
        except KeyboardInterrupt:
            # Ctrl+C durante a resposta interrompe só a resposta, não o programa.
            write("\n[resposta interrompida]\n")


def _describe(settings: Settings) -> str:
    tracing = (
        f"ativo (projeto: {settings.langsmith_project or 'default'})"
        if settings.langsmith_tracing
        else "desativado"
    )
    return f"Modelo: {settings.model} | Tracing LangSmith: {tracing}\n"


def main() -> int:
    """Ponto de entrada: `python -m chatbot`. Retorna o código de saída."""
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 1

    store = SessionStore()
    chain = build_chain(build_llm(settings), store, settings.max_history_messages)

    print("=== Tutor de Python ===")
    print(_describe(settings))
    try:
        run_chat(chain, store)
    except FatalChatError as exc:
        print(f"\nErro: {exc}", file=sys.stderr)
        return 1
    return 0
