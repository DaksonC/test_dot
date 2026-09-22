"""Ponto de entrada da API. Rodar com: uvicorn app.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers import books


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Cria as tabelas na subida da aplicação. Em um projeto maior, usaríamos
    # migrações (Alembic) em vez de create_all.
    create_db_and_tables()
    yield


app = FastAPI(
    title="Biblioteca Virtual",
    description="API para cadastro e consulta de livros.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(books.router)
