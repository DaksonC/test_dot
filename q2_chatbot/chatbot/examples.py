"""Gera EXEMPLOS.md com perguntas e respostas reais do modelo.

Uso: python -m chatbot.examples

As perguntas rodam na MESMA sessão, então a segunda pergunta ("E como
adiciono...") só faz sentido se a memória da conversa estiver funcionando.

O arquivo é regravado após cada resposta: se a API falhar no meio (ex.: falta
de crédito), as respostas já obtidas não se perdem e o arquivo indica que
ficou incompleto.
"""

import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

import openai
from langchain_core.runnables import Runnable

from chatbot.chain import SessionStore, build_chain, build_llm
from chatbot.config import ConfigError, load_settings

EXAMPLE_QUESTIONS = [
    "Como criar uma lista em Python?",
    "E como eu adiciono e removo itens nela?",
    "Qual a diferença entre lista e tupla? Quando usar cada uma?",
    "Como ler um arquivo CSV em Python?",
]

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "EXEMPLOS.md"

# Mais tentativas que o padrão do SDK (2): o script faz chamadas em sequência e
# costuma esbarrar no limite por minuto. O SDK espera com backoff exponencial
# entre as tentativas e respeita o header x-should-retry, então erros que não
# adianta repetir (como falta de crédito) não são retentados.
EXAMPLES_MAX_RETRIES = 5


def describe_api_error(exc: openai.APIError) -> str:
    """Traduz o erro da OpenAI numa mensagem com a ação que o usuário deve tomar."""
    if isinstance(exc, openai.RateLimitError):
        # O 429 tem duas causas bem diferentes, distinguíveis pelo código do erro.
        if exc.code == "insufficient_quota":
            return (
                "Sem crédito na conta da OpenAI (insufficient_quota). "
                "Adicione crédito em platform.openai.com > Billing e rode de novo."
            )
        return (
            "Limite de requisições por minuto atingido mesmo após novas tentativas. "
            "Aguarde um pouco e rode de novo."
        )
    if isinstance(exc, openai.AuthenticationError):
        return "Chave da OpenAI inválida. Verifique OPENAI_API_KEY."
    if isinstance(exc, openai.NotFoundError):
        return "Modelo não encontrado ou sem acesso. Verifique OPENAI_MODEL."
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
        return "Falha de conexão com a OpenAI. Verifique a internet e rode de novo."
    return f"A OpenAI retornou um erro: {exc}"


def render_markdown(model: str, answered: Sequence[tuple[str, str]], total: int) -> str:
    """Monta o EXEMPLOS.md; marca como incompleto se nem todas as perguntas foram respondidas."""
    parts = [
        "# Exemplos reais de perguntas e respostas\n",
        f"Gerado por `python -m chatbot.examples` em {date.today().isoformat()} "
        f"com o modelo `{model}`. As perguntas rodam na mesma sessão "
        "(a 2ª depende da memória da conversa).\n",
    ]
    if len(answered) < total:
        parts.append(
            f"\n> **Incompleto:** {len(answered)} de {total} perguntas respondidas "
            "(a geração foi interrompida por erro da API).\n"
        )
    for i, (question, answer) in enumerate(answered, start=1):
        parts.append(f"\n---\n\n## {i}. {question}\n\n{answer.strip()}\n")
    return "".join(parts)


def generate_examples(
    chain: Runnable,
    model: str,
    output_file: Path,
    questions: Sequence[str] = EXAMPLE_QUESTIONS,
    log: Callable[[str], None] = print,
) -> bool:
    """Responde as perguntas em sequência, salvando o arquivo a cada resposta.

    Retorna True se todas foram respondidas. A chain é injetada para permitir
    testes com um LLM falso.
    """
    config = {"configurable": {"session_id": "exemplos"}}
    answered: list[tuple[str, str]] = []

    for i, question in enumerate(questions, start=1):
        log(f"[{i}/{len(questions)}] {question}")
        try:
            answer = chain.invoke({"question": question}, config=config)
        except openai.APIError as exc:
            log(f"Erro na pergunta {i}: {describe_api_error(exc)}")
            break
        answered.append((question, answer))
        output_file.write_text(render_markdown(model, answered, len(questions)), encoding="utf-8")

    if not answered:
        # Nada foi gerado: não cria nem sobrescreve o arquivo com um documento vazio.
        return False

    log(f"{len(answered)}/{len(questions)} respostas salvas em {output_file}")
    return len(answered) == len(questions)


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 1

    store = SessionStore()
    llm = build_llm(settings, max_retries=EXAMPLES_MAX_RETRIES)
    chain = build_chain(llm, store, settings.max_history_messages)

    ok = generate_examples(chain, settings.model, OUTPUT_FILE)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
