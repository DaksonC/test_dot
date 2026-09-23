"""Garante que as consultas de demonstração não compartilham palavras com o esperado."""

import pytest

from semantic_search.config import DATA_FILE
from semantic_search.demo import DEMO_QUERIES, shared_terms
from semantic_search.documents import Document, load_documents

DOCUMENTS = {doc.id: doc for doc in load_documents(DATA_FILE)}


@pytest.mark.parametrize(("query", "expected_id"), DEMO_QUERIES)
def test_demo_query_has_no_keyword_in_common_with_expected_document(query, expected_id):
    assert shared_terms(query, DOCUMENTS[expected_id]) == set()


def test_shared_terms_ignores_case_accents_and_plural():
    document = Document("d", "Joelhos", "c", "Proteção")

    assert shared_terms("JOELHO e protecao", document) == {"joelh", "prote"}
