# Q1 — API de Biblioteca Virtual

API REST para **cadastrar e consultar livros**, feita com **FastAPI + SQLModel + SQLite**.

## Como instalar

```bash
cd q1_api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Como rodar

```bash
uvicorn app.main:app --reload
```

- Swagger (documentação interativa, com exemplos): http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

As tabelas são criadas automaticamente na subida, em `./library.db`.
Para usar outro arquivo: `DATABASE_URL=sqlite:///./outro.db uvicorn app.main:app`.

## Como testar

```bash
pytest
```

Os testes rodam em um SQLite **em memória**, isolado por teste, e nunca tocam o `library.db`.

## Endpoints

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| `POST` | `/books` | Cadastra um livro | `201` criado · `422` payload inválido |
| `GET` | `/books` | Consulta por título e/ou autor, paginada | `200` · `422` paginação inválida |
| `GET` | `/books/{book_id}` | Obtém um livro pelo id | `200` · `404` não encontrado · `422` id não inteiro |

### Regras de validação (POST)

- `title` e `author`: obrigatórios, 1 a 200 caracteres, espaços nas pontas são removidos, e string só com espaços é rejeitada.
- `published_date`: formato ISO `AAAA-MM-DD`, e não pode estar no futuro.
- `summary`: obrigatório, até 5000 caracteres.

### Regras da consulta (GET /books)

| Parâmetro | Comportamento |
|---|---|
| `title`, `author` | Match **parcial** e **sem diferenciar maiúsculas**, inclusive com acentos (`ANÉIS` encontra `Anéis`). Com os dois filtros, a combinação é **AND**. Valor vazio é ignorado. `%` e `_` são tratados como texto, não como curinga. |
| `offset` | Quantos resultados pular (≥ 0, padrão 0). |
| `limit` | Máximo de resultados (1 a 100, padrão 20). |

Sem filtros, lista todos os livros. A ordem é sempre por `id`.

## Exemplos de uso

```bash
# Cadastrar
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "O Hobbit", "author": "J.R.R. Tolkien",
       "published_date": "1937-09-21", "summary": "Bilbo parte em aventura."}'
# -> 201 {"title":"O Hobbit","author":"J.R.R. Tolkien","published_date":"1937-09-21","summary":"...","id":1}

# Buscar por autor (parcial, case-insensitive)
curl "http://127.0.0.1:8000/books?author=TOLKIEN"

# Buscar por título e autor (AND)
curl "http://127.0.0.1:8000/books?title=hobbit&author=tolkien"

# Obter por id
curl http://127.0.0.1:8000/books/1
# -> 404 {"detail":"Livro não encontrado"} se não existir
```

## Estrutura

```
app/
├── main.py          # app FastAPI + lifespan (cria as tabelas na subida)
├── database.py      # build_engine (lower() Unicode), get_session, SessionDep
├── models.py        # BookBase / Book (tabela) / BookCreate (validações) / BookRead
├── crud.py          # acesso a dados, sem conhecimento de HTTP
└── routers/books.py # endpoints e documentação OpenAPI
tests/
├── conftest.py      # SQLite em memória (StaticPool) + dependency override
└── test_books.py    # sucesso, filtros, 404 e 422
```

## Decisões técnicas

- **FastAPI + SQLModel:** um único modelo serve de schema Pydantic e de tabela SQLAlchemy, e a documentação OpenAPI sai dos próprios tipos.
- **Modelos separados por papel** (`BookCreate` / `BookRead` / `Book`): o cliente não consegue mandar `id`, a resposta sempre traz `id`, e as regras de entrada ficam isoladas. Isso importa porque modelos `table=True` **não** validam no construtor.
- **Camada `crud` sem HTTP:** os endpoints só traduzem para status codes, e a lógica pode ser reaproveitada ou testada sem o servidor.
- **Busca com `GET /books?title=&author=`** em vez de `/books/search`: filtro é query param do recurso de coleção (REST).
- **`lower()` Unicode no SQLite:** o `lower()` nativo só converte ASCII (`lower('ANÉIS') = 'anÉis'`). O `build_engine` registra o `str.lower` do Python na conexão. A troca vale para aplicação e testes, porque os dois usam a mesma fábrica de engine.
- **Escape de curingas (`autoescape=True`):** evita que `%` ou `_` digitados pelo usuário retornem resultados inesperados. A query é sempre parametrizada, então não há risco de SQL injection.
- **Paginação com limite máximo (100)** e ordenação por `id`: respostas limitadas e paginação determinística.
- **Testes com `StaticPool`:** um SQLite `sqlite://` abre um banco novo e vazio a cada conexão. O `StaticPool` reutiliza a mesma conexão, e o `dependency_overrides` injeta essa sessão nos endpoints.

### Limitações conhecidas

- A busca não ignora acentos: `aneis` não encontra `Anéis`. Seria resolvido com uma coluna normalizada (sem acentos) ou com busca full-text (FTS5).
- `LIKE '%termo%'` não usa índice e faz varredura da tabela. Isso é suficiente para o escopo, mas para grandes volumes o caminho seria FTS5, Postgres com `pg_trgm` ou um motor de busca.
- `create_all` na subida no lugar de migrações (Alembic), o que é adequado para um projeto de exemplo.
