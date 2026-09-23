"""Testes do índice FAISS e da persistência em disco."""

import json

import numpy as np
import pytest

from semantic_search.store import (
    DOCUMENTS_FILE,
    META_FILE,
    IndexCorruptedError,
    IndexNotFoundError,
    build_store,
    load_store,
    save_store,
)
from tests.conftest import DOCS


def test_build_indexes_every_document(store, embedder):
    assert store.size == len(DOCS)
    assert store.index.d == embedder.dimension
    assert store.model_name == embedder.model_name


def test_build_without_documents_raises(embedder):
    with pytest.raises(ValueError):
        build_store([], embedder)


def test_stored_vectors_are_normalized(store):
    vectors = store.index.reconstruct_n(0, store.size)

    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5)


def test_save_and_load_roundtrip(store, tmp_path):
    save_store(store, tmp_path)
    loaded = load_store(tmp_path)

    assert loaded.documents == store.documents
    assert loaded.model_name == store.model_name
    np.testing.assert_array_equal(
        loaded.index.reconstruct_n(0, loaded.size), store.index.reconstruct_n(0, store.size)
    )


def test_meta_records_model_and_dimension(store, tmp_path):
    save_store(store, tmp_path)
    meta = json.loads((tmp_path / META_FILE).read_text())

    assert meta["model_name"] == "fake-model"
    assert meta["dimension"] == 64
    assert meta["num_documents"] == len(DOCS)


def test_load_missing_index_raises_with_hint(tmp_path):
    with pytest.raises(IndexNotFoundError, match="semantic_search.build"):
        load_store(tmp_path / "nao-existe")


def test_load_inconsistent_files_raises(store, tmp_path):
    save_store(store, tmp_path)
    documents = json.loads((tmp_path / DOCUMENTS_FILE).read_text())
    (tmp_path / DOCUMENTS_FILE).write_text(json.dumps(documents[:-1]))  # um documento a menos

    with pytest.raises(IndexCorruptedError):
        load_store(tmp_path)
