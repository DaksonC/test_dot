"""Testes da função de busca: ordenação, formato dos resultados e validações."""

import pytest

from semantic_search.documents import Document
from semantic_search.search import SearchResult, SemanticSearcher
from tests.conftest import DOCS, FakeEmbedder


@pytest.fixture
def searcher(store, embedder) -> SemanticSearcher:
    return SemanticSearcher(store, embedder)


def test_returns_k_results_in_expected_format(searcher):
    results = searcher.search("gato água", k=3)

    assert len(results) == 3
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(isinstance(r.document, Document) and isinstance(r.score, float) for r in results)


def test_most_similar_document_comes_first(searcher):
    results = searcher.search("medo de barulho de fogos", k=2)

    assert results[0].document.id == "cao"


def test_results_are_sorted_by_descending_score(searcher):
    scores = [r.score for r in searcher.search("gato pão juros", k=4)]

    assert scores == sorted(scores, reverse=True)


def test_scores_are_cosine_similarities(searcher):
    # Vetores normalizados: produto interno = cosseno, então fica em [-1, 1]
    # e um texto idêntico ao indexado tem score ~1.
    [top] = searcher.search(DOCS[2].content_for_embedding(), k=1)

    assert top.document.id == "pao"
    assert top.score == pytest.approx(1.0, abs=1e-5)


def test_k_larger_than_collection_returns_all(searcher):
    results = searcher.search("qualquer coisa", k=100)

    assert len(results) == len(DOCS)
    assert len({r.document.id for r in results}) == len(DOCS)


@pytest.mark.parametrize("k", [0, -1])
def test_invalid_k_raises(searcher, k):
    with pytest.raises(ValueError, match="k"):
        searcher.search("gato", k=k)


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query_raises(searcher, query):
    with pytest.raises(ValueError, match="vazia"):
        searcher.search(query)


def test_model_mismatch_between_index_and_embedder_raises(store):
    with pytest.raises(ValueError, match="Reconstrua"):
        SemanticSearcher(store, FakeEmbedder(model_name="outro-modelo"))


def test_from_directory_loads_persisted_index(store, embedder, tmp_path):
    from semantic_search.store import save_store

    save_store(store, tmp_path)
    searcher = SemanticSearcher.from_directory(tmp_path, embedder=embedder)

    assert searcher.search("juros e dinheiro", k=1)[0].document.id == "juros"
