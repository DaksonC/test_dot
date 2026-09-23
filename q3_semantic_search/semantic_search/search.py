"""Função de busca semântica sobre o índice persistido."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from semantic_search.config import INDEX_DIR
from semantic_search.documents import Document
from semantic_search.embeddings import Embedder, SentenceTransformerEmbedder
from semantic_search.store import VectorStore, load_store


@dataclass(frozen=True)
class SearchResult:
    document: Document
    # Similaridade de cosseno em [-1, 1]; quanto maior, mais parecido.
    score: float


class SemanticSearcher:
    """Combina um VectorStore com o embedder que o gerou."""

    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        # Vetores de modelos diferentes vivem em espaços diferentes: comparar a
        # consulta de um modelo com documentos de outro dá resultados sem sentido.
        if store.model_name != embedder.model_name:
            raise ValueError(
                f"O índice foi gerado com {store.model_name!r}, mas o embedder é "
                f"{embedder.model_name!r}. Reconstrua o índice ou use o mesmo modelo."
            )
        self._store = store
        self._embedder = embedder

    @classmethod
    def from_directory(cls, directory: Path = INDEX_DIR, embedder: Embedder | None = None) -> "SemanticSearcher":
        store = load_store(directory)
        return cls(store, embedder or SentenceTransformerEmbedder(store.model_name))

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Retorna os k documentos mais similares à consulta, do mais ao menos relevante."""
        if not query or not query.strip():
            raise ValueError("A consulta não pode ser vazia.")
        if k < 1:
            raise ValueError("k deve ser maior ou igual a 1.")

        # Pedir mais vizinhos do que existem faz o FAISS preencher com id -1.
        k = min(k, self._store.size)
        query_vector = self._embedder.encode([query.strip()])
        scores, ids = self._store.index.search(query_vector, k)

        # FAISS devolve matrizes (n_consultas, k); aqui há uma consulta só.
        return [
            SearchResult(document=self._store.documents[i], score=float(score))
            for score, i in zip(scores[0], ids[0], strict=True)
            if i != -1
        ]


@lru_cache(maxsize=1)
def get_default_searcher() -> SemanticSearcher:
    """Carrega índice e modelo uma única vez por processo (a carga é o passo caro)."""
    return SemanticSearcher.from_directory(INDEX_DIR)


def search(query: str, k: int = 5) -> list[SearchResult]:
    """Atalho: busca no índice padrão em disco (gerado por `python -m semantic_search.build`)."""
    return get_default_searcher().search(query, k)
