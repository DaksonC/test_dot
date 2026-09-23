"""Fixtures com um embedder falso: testes rápidos, determinísticos e sem download."""

import hashlib
import re
from collections.abc import Sequence

import numpy as np
import pytest

from semantic_search.documents import Document
from semantic_search.store import build_store


class FakeEmbedder:
    """Bag-of-words com hashing: textos com palavras em comum ficam próximos.

    Não é semântico, mas respeita o contrato do Embedder (float32, norma 1),
    o que basta para testar índice, ordenação, persistência e validações.
    """

    def __init__(self, model_name: str = "fake-model", dimension: int = 64) -> None:
        self.model_name = model_name
        self.dimension = dimension

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"\w+", text.lower()):
                bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimension
                vectors[row, bucket] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)


DOCS = [
    Document("gato", "Gato bebendo água", "animais", "gato água fonte hidratação"),
    Document("cao", "Cão com medo", "animais", "cão medo barulho fogos"),
    Document("pao", "Pão caseiro", "culinária", "pão farinha fermento forno"),
    Document("juros", "Juros compostos", "finanças", "juros capital rendimento dinheiro"),
]


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def store(embedder):
    return build_store(DOCS, embedder)
