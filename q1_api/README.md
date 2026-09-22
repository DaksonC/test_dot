# Q1 — API de Biblioteca Virtual

API REST para cadastrar e consultar livros, feita com **FastAPI + SQLModel + SQLite**.

## Como rodar

```bash
cd q1_api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentação interativa: http://127.0.0.1:8000/docs (Swagger) ou `/redoc`.

O banco é criado em `./library.db` na subida. Para usar outro arquivo:
`DATABASE_URL=sqlite:///./outro.db uvicorn app.main:app`.

## Endpoints

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| `POST` | `/books` | Cadastra um livro | `201`, `422` |
| `GET` | `/books?title=&author=&offset=0&limit=20` | Busca por título e/ou autor | `200`, `422` |
| `GET` | `/books/{book_id}` | Obtém um livro pelo id | `200`, `404` |

Regras da busca: match parcial e case-insensitive; `title` + `author` combinam com **AND**;
sem filtros lista todos; `limit` entre 1 e 100; ordenação por `id`.

### Exemplo

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "O Hobbit", "author": "J.R.R. Tolkien", "published_date": "1937-09-21", "summary": "Bilbo parte em aventura."}'

curl "http://127.0.0.1:8000/books?author=tolkien"
```

## Estrutura

```
app/
├── main.py          # app FastAPI + lifespan (cria tabelas)
├── database.py      # engine, get_session (dependência)
├── models.py        # BookBase / Book (tabela) / BookCreate / BookRead
├── crud.py          # acesso a dados, sem conhecimento de HTTP
└── routers/books.py # endpoints
tests/
├── conftest.py      # SQLite em memória (StaticPool) + dependency override
└── test_books.py
```

## Testes

```bash
pytest
```

Os testes usam SQLite em memória (`sqlite://` + `StaticPool`), injetado via
`app.dependency_overrides[get_session]`. O banco real não é tocado.
