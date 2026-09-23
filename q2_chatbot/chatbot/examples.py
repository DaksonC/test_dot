"""Gera EXEMPLOS.md com perguntas e respostas reais do modelo.

Uso: python -m chatbot.examples

As perguntas rodam na MESMA sessão, então a segunda pergunta ("E como
adiciono...") só faz sentido se a memória da conversa estiver funcionando.
"""

import sys
from datetime import date
from pathlib import Path

from chatbot.chain import SessionStore, build_chain, build_llm
from chatbot.config import ConfigError, load_settings

EXAMPLE_QUESTIONS = [
    "Como criar uma lista em Python?",
    "E como eu adiciono e removo itens nela?",
    "Qual a diferença entre lista e tupla? Quando usar cada uma?",
    "Como ler um arquivo CSV em Python?",
]

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "EXEMPLOS.md"


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 1

    store = SessionStore()
    chain = build_chain(build_llm(settings), store, settings.max_history_messages)
    config = {"configurable": {"session_id": "exemplos"}}

    parts = [
        "# Exemplos reais de perguntas e respostas\n",
        f"Gerado por `python -m chatbot.examples` em {date.today().isoformat()} "
        f"com o modelo `{settings.model}`. As perguntas rodam na mesma sessão "
        "(a 2ª depende da memória da conversa).\n",
    ]
    for i, question in enumerate(EXAMPLE_QUESTIONS, start=1):
        print(f"[{i}/{len(EXAMPLE_QUESTIONS)}] {question}")
        answer = chain.invoke({"question": question}, config=config)
        parts.append(f"\n---\n\n## {i}. {question}\n\n{answer.strip()}\n")

    OUTPUT_FILE.write_text("".join(parts), encoding="utf-8")
    print(f"Exemplos salvos em {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
