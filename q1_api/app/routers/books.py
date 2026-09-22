"""Endpoints de livros.

Os handlers são finos: validam entrada (via tipos/Query), delegam ao crud
e traduzem o resultado para HTTP (status codes, 404).
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.database import SessionDep
from app.models import BookCreate, BookRead

router = APIRouter(prefix="/books", tags=["books"])


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar livro",
    description="Cadastra um livro com título, autor, data de publicação e resumo.",
)
def create_book(book: BookCreate, session: SessionDep) -> BookRead:
    return crud.create_book(session, book)


@router.get(
    "",
    response_model=list[BookRead],
    summary="Consultar livros",
    description=(
        "Lista livros filtrando por título e/ou autor (match parcial, sem diferenciar "
        "maiúsculas/minúsculas). Com os dois filtros, ambos precisam bater. "
        "Filtros vazios são ignorados. Sem filtros, lista todos. "
        "Resultado ordenado por id e paginado por `offset`/`limit`."
    ),
)
def search_books(
    session: SessionDep,
    title: Annotated[
        str | None, Query(max_length=200, description="Trecho do título", examples=["anéis"])
    ] = None,
    author: Annotated[
        str | None, Query(max_length=200, description="Trecho do nome do autor", examples=["tolkien"])
    ] = None,
    offset: Annotated[int, Query(ge=0, description="Quantos resultados pular")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de resultados (1 a 100)")] = 20,
) -> list[BookRead]:
    return crud.search_books(session, title=title, author=author, offset=offset, limit=limit)


@router.get(
    "/{book_id}",
    response_model=BookRead,
    summary="Obter livro por id",
    responses={404: {"description": "Livro não encontrado"}},
)
def get_book(book_id: int, session: SessionDep) -> BookRead:
    book = crud.get_book(session, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")
    return book
