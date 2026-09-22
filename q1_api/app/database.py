"""Configuração do banco de dados (SQLite via SQLModel/SQLAlchemy)."""

import os
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

# A URL pode ser sobrescrita por variável de ambiente (ex.: outro arquivo em produção).
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./library.db"


def _unicode_lower(value: str | None) -> str | None:
    return value.lower() if value is not None else None


def build_engine(url: str, **kwargs: Any) -> Engine:
    """Cria a engine do SQLite já com as customizações da aplicação.

    Centralizar aqui garante que a aplicação e os testes usem exatamente
    o mesmo comportamento de banco, mudando apenas a URL/pool.
    """
    # check_same_thread=False: o FastAPI pode atender a requisição em uma thread
    # diferente da que abriu a conexão; o SQLite bloqueia isso por padrão.
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    @event.listens_for(engine, "connect")
    def _register_functions(dbapi_connection: Any, _: Any) -> None:
        # O lower() nativo do SQLite só converte ASCII: lower('ANÉIS') = 'anÉis'.
        # Sobrescrevemos com o str.lower do Python para a busca case-insensitive
        # funcionar com acentos, comuns em títulos e autores em português.
        dbapi_connection.create_function("lower", 1, _unicode_lower, deterministic=True)

    return engine


engine = build_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    """Cria as tabelas registradas no metadata do SQLModel (idempotente)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e a fecha ao final.

    Nos testes, esta função é substituída via `app.dependency_overrides`
    por uma sessão ligada a um banco em memória.
    """
    with Session(engine) as session:
        yield session


# Atalho tipado para injetar a sessão nos endpoints.
SessionDep = Annotated[Session, Depends(get_session)]
