"""Geração de embeddings.

O resto do código depende só do protocolo `Embedder`, o que permite trocar o
modelo (ou usar um embedder falso nos testes) sem mexer no índice e na busca.
"""

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from semantic_search.config import DEFAULT_MODEL_NAME


class Embedder(Protocol):
    model_name: str
    dimension: int

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Retorna matriz (len(texts), dimension), float32, com cada linha de norma 1."""
        ...


class SentenceTransformerEmbedder:
    """Embedder baseado em sentence-transformers (Hugging Face)."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        # Import tardio: carregar torch/transformers leva alguns segundos e só é
        # necessário quando um embedder real é de fato criado.
        from sentence_transformers import SentenceTransformer

        # Na primeira execução o modelo (~470 MB) é baixado e fica em cache local.
        self._model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = int(self._model.get_embedding_dimension())

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            batch_size=32,
            convert_to_numpy=True,
            # Normalizar (norma L2 = 1) faz o produto interno ser igual ao
            # cosseno, que é a métrica que o IndexFlatIP calcula.
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        # FAISS exige float32 e memória contígua.
        return np.ascontiguousarray(vectors, dtype=np.float32)
