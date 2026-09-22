"""Configuração do banco de dados (SQLite via SQLModel/SQLAlchemy)."""

import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

# A URL pode ser sobrescrita por variável de ambiente (ex.: outro arquivo em produção).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./library.db")

# check_same_thread=False: o FastAPI pode atender a requisição em uma thread
# diferente da que abriu a conexão; o SQLite bloqueia isso por padrão.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


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
