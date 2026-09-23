"""Testes do carregamento e validação do conjunto de documentos."""

import pytest

from semantic_search.config import DATA_FILE
from semantic_search.documents import load_documents, parse_documents


def _doc(**overrides) -> dict:
    return {"id": "x", "title": "Título", "category": "cat", "text": "Texto."} | overrides


def test_dataset_is_valid_and_has_20_to_30_documents():
    documents = load_documents(DATA_FILE)

    assert 20 <= len(documents) <= 30
    assert len({d.category for d in documents}) >= 8  # temas variados


def test_duplicate_id_raises():
    with pytest.raises(ValueError, match="duplicado"):
        parse_documents([_doc(), _doc()])


@pytest.mark.parametrize("field", ["id", "title", "category", "text"])
def test_missing_or_blank_field_raises(field):
    with pytest.raises(ValueError, match=field):
        parse_documents([_doc(**{field: "  "})])


def test_empty_list_raises():
    with pytest.raises(ValueError):
        parse_documents([])


def test_embedding_text_includes_title():
    [document] = parse_documents([_doc(title="Eclipse", text="A Lua cobre o Sol.")])

    assert document.content_for_embedding() == "Eclipse. A Lua cobre o Sol."
