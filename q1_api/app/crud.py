"""Camada de acesso a dados.

Não conhece HTTP (sem HTTPException, status codes etc.): recebe uma Session
e dados já validados, e devolve objetos do domínio. Isso facilita testar e
reaproveitar a lógica fora da API.
"""

from sqlmodel import Session

from app.models import Book, BookCreate


def create_book(session: Session, data: BookCreate) -> Book:
    """Persiste um novo livro e o retorna com o id preenchido."""
    # TODO: converter BookCreate -> Book, adicionar, commitar e dar refresh.
    raise NotImplementedError


def get_book(session: Session, book_id: int) -> Book | None:
    """Retorna o livro pelo id, ou None se não existir."""
    # TODO
    raise NotImplementedError


def search_books(
    session: Session,
    title: str | None = None,
    author: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Book]:
    """Busca livros por título e/ou autor.

    Regras:
    - match parcial e case-insensitive ("tolkien" encontra "J.R.R. Tolkien");
    - se title e author forem informados, ambos devem bater (AND);
    - sem filtros, lista todos;
    - ordenado por id para paginação determinística.
    """
    # TODO
    raise NotImplementedError
