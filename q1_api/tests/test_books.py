"""Testes dos endpoints /books."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models import Book


def titles(response) -> list[str]:
    return [book["title"] for book in response.json()]


# --------------------------------------------------------------------------- #
# POST /books
# --------------------------------------------------------------------------- #

def test_create_book_returns_201_with_id(client: TestClient, book_payload: dict):
    response = client.post("/books", json=book_payload)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert {k: body[k] for k in book_payload} == book_payload


@pytest.mark.parametrize("missing", ["title", "author", "published_date", "summary"])
def test_create_book_missing_field_returns_422(client: TestClient, book_payload: dict, missing: str):
    del book_payload[missing]

    response = client.post("/books", json=book_payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["title", "author"])
def test_create_book_blank_field_returns_422(client: TestClient, book_payload: dict, field: str):
    book_payload[field] = "   "

    response = client.post("/books", json=book_payload)

    assert response.status_code == 422


def test_create_book_strips_whitespace(client: TestClient, book_payload: dict):
    book_payload["title"] = "  O Hobbit  "

    response = client.post("/books", json=book_payload)

    assert response.status_code == 201
    assert response.json()["title"] == "O Hobbit"


def test_create_book_future_date_returns_422(client: TestClient, book_payload: dict):
    book_payload["published_date"] = (date.today() + timedelta(days=1)).isoformat()

    response = client.post("/books", json=book_payload)

    assert response.status_code == 422


def test_create_book_invalid_date_format_returns_422(client: TestClient, book_payload: dict):
    book_payload["published_date"] = "29/07/1954"

    response = client.post("/books", json=book_payload)

    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# GET /books/{id}
# --------------------------------------------------------------------------- #

def test_get_book_by_id(client: TestClient, seeded_books: list[Book]):
    target = seeded_books[2]

    response = client.get(f"/books/{target.id}")

    assert response.status_code == 200
    assert response.json()["title"] == target.title


def test_get_book_not_found_returns_404(client: TestClient):
    response = client.get("/books/9999")

    assert response.status_code == 404


def test_created_book_can_be_fetched(client: TestClient, book_payload: dict):
    created = client.post("/books", json=book_payload).json()

    response = client.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


# --------------------------------------------------------------------------- #
# GET /books (busca)
# --------------------------------------------------------------------------- #

def test_search_by_title_partial_case_insensitive(client: TestClient, seeded_books):
    response = client.get("/books", params={"title": "hOBBit"})

    assert response.status_code == 200
    assert titles(response) == ["O Hobbit"]


def test_search_by_author(client: TestClient, seeded_books):
    response = client.get("/books", params={"author": "machado"})

    assert response.status_code == 200
    assert titles(response) == ["Dom Casmurro", "Memórias Póstumas de Brás Cubas"]


def test_search_by_title_and_author_uses_and(client: TestClient, seeded_books):
    # "o" sozinho bate em todos os 5 títulos; o filtro de autor restringe a 2.
    # Se a combinação fosse OR, viriam os 5.
    response = client.get("/books", params={"title": "o", "author": "tolkien"})

    assert response.status_code == 200
    assert titles(response) == ["O Senhor dos Anéis", "O Hobbit"]


def test_search_without_filters_lists_all(client: TestClient, seeded_books):
    response = client.get("/books")

    assert response.status_code == 200
    assert len(response.json()) == len(seeded_books)


def test_search_no_match_returns_empty_list(client: TestClient, seeded_books):
    response = client.get("/books", params={"title": "inexistente"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_respects_limit_and_offset(client: TestClient, seeded_books):
    response = client.get("/books", params={"offset": 1, "limit": 2})

    assert response.status_code == 200
    assert titles(response) == [seeded_books[1].title, seeded_books[2].title]


@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"offset": -1}])
def test_invalid_pagination_returns_422(client: TestClient, params: dict):
    response = client.get("/books", params=params)

    assert response.status_code == 422
