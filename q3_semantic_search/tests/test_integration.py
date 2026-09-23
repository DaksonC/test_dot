"""Integração com o modelo real e o índice em disco.

Rode com: pytest -m integration   (requer `python -m semantic_search.build` antes)
"""

import numpy as np
import pytest

from semantic_search.demo import DEMO_QUERIES

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_searcher():
    from semantic_search.search import SemanticSearcher

    return SemanticSearcher.from_directory()


def test_real_embeddings_are_normalized():
    from semantic_search.embeddings import SentenceTransformerEmbedder

    vectors = SentenceTransformerEmbedder().encode(["Como criar uma lista?", "Receita de pão"])

    assert vectors.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5)


@pytest.mark.parametrize(("query", "expected_id"), DEMO_QUERIES)
def test_expected_document_is_in_top_3(real_searcher, query, expected_id):
    # O limiar é top-3 (hit@3), não top-1: o README discute as consultas em
    # que o modelo pequeno erra o 1º lugar.
    ids = [r.document.id for r in real_searcher.search(query, k=3)]

    assert expected_id in ids


def test_public_search_function_uses_persisted_index():
    from semantic_search import search

    results = search("pesticidas estão matando os insetos que fabricam mel", k=2)

    assert len(results) == 2
    assert results[0].document.id == "meio-ambiente-abelhas"
    assert results[0].score > results[1].score
