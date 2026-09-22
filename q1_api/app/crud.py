"""Camada de acesso a dados.

Não conhece HTTP (sem HTTPException, status codes etc.): recebe uma Session
e dados já validados, e devolve objetos do domínio. Isso facilita testar e
reaproveitar a lógica fora da API.
"""

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Book, BookCreate


def create_book(session: Session, data: BookCreate) -> Book:
    """Persiste um novo livro e o retorna com o id preenchido."""
    # model_validate copia os campos já validados de BookCreate para a tabela.
    book = Book.model_validate(data)
    session.add(book)
    session.commit()
    # refresh recarrega do banco os valores gerados por ele (o id autoincrement).
    session.refresh(book)
    return book


def get_book(session: Session, book_id: int) -> Book | None:
    """Retorna o livro pelo id, ou None se não existir."""
    return session.get(Book, book_id)


def _normalize_term(term: str | None) -> str | None:
    """Filtro ausente, vazio ou só com espaços significa "sem filtro"."""
    if term is None:
        return None
    term = term.strip()
    return term or None


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
    statement = select(Book)

    # Cada filtro vira um LIKE '%termo%' sobre lower(coluna). Chamar .where()
    # mais de uma vez combina as condições com AND.
    # autoescape=True escapa '%' e '_' digitados pelo usuário, para que sejam
    # tratados como texto literal e não como curingas do LIKE.
    for column, term in ((Book.title, title), (Book.author, author)):
        term = _normalize_term(term)
        if term is not None:
            statement = statement.where(
                func.lower(column).contains(term.lower(), autoescape=True)
            )

    statement = statement.order_by(col(Book.id)).offset(offset).limit(limit)
    return list(session.exec(statement).all())
