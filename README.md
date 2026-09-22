# Prova — Desenvolvedor Backend com foco em IA

Soluções para as 3 questões da prova técnica. Cada questão é independente:
tem código, `README.md` e `requirements.txt` próprios.

| Pasta | Questão | Stack |
|---|---|---|
| [`q1_api/`](q1_api/README.md) | API de cadastro e consulta de livros | FastAPI, SQLModel, SQLite, pytest |
| [`q2_chatbot/`](q2_chatbot/README.md) | Chatbot tutor de Python com LLM | LangChain, OpenAI, LangSmith (opcional) |
| [`q3_semantic_search/`](q3_semantic_search/README.md) | Busca semântica com embeddings | sentence-transformers, FAISS |

## Requisitos

- Python 3.11+
- Um ambiente virtual por questão (recomendado):

```bash
cd q1_api            # ou q2_chatbot / q3_semantic_search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Variáveis de ambiente

As variáveis usadas estão documentadas em [`.env.example`](.env.example).
Copie para `.env` e preencha. O `.env` está no `.gitignore` e nenhuma chave
é escrita no código.
