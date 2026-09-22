"""Fixtures compartilhadas: banco SQLite em memória isolado por teste."""

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from app.database import build_engine, get_session
from app.main import app
from app.models import Book


@pytest.fixture(name="session")
def session_fixture() -> Iterator[Session]:
    # "sqlite://" = banco em memória. Cada conexão nova abriria um banco VAZIO;
    # o StaticPool faz todas as sessões reutilizarem a mesma conexão.
    # build_engine é o mesmo da aplicação, então o lower() Unicode vale aqui também.
    engine = build_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    # Sem "with TestClient(...)": o lifespan não roda, então o library.db real
    # não é criado/tocado durante os testes.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def book_payload() -> dict:
    """Payload válido de POST /books; os testes alteram só o campo que interessa."""
    return {
        "title": "O Senhor dos Anéis",
        "author": "J.R.R. Tolkien",
        "published_date": "1954-07-29",
        "summary": "Uma jornada para destruir o Um Anel.",
    }


@pytest.fixture
def seeded_books(session: Session) -> list[Book]:
    """Insere livros direto no banco, sem passar pela API.

    Assim os testes de busca não dependem do POST estar implementado.
    """
    books = [
        Book(title="O Senhor dos Anéis", author="J.R.R. Tolkien",
             published_date=date(1954, 7, 29), summary="Fantasia épica."),
        Book(title="O Hobbit", author="J.R.R. Tolkien",
             published_date=date(1937, 9, 21), summary="Bilbo parte em aventura."),
        Book(title="Dom Casmurro", author="Machado de Assis",
             published_date=date(1899, 1, 1), summary="Capitu e Bentinho."),
        Book(title="Memórias Póstumas de Brás Cubas", author="Machado de Assis",
             published_date=date(1881, 1, 1), summary="Narrado por um defunto autor."),
        Book(title="Clean Code", author="Robert C. Martin",
             published_date=date(2008, 8, 1), summary="Boas práticas de código."),
    ]
    session.add_all(books)
    session.commit()
    for book in books:
        session.refresh(book)
    return books
