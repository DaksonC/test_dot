"""Constrói o índice a partir de data/documents.json e o salva em index/.

Uso: python -m semantic_search.build
"""

import sys
import time

from semantic_search.config import DATA_FILE, DEFAULT_MODEL_NAME, INDEX_DIR
from semantic_search.documents import load_documents
from semantic_search.embeddings import SentenceTransformerEmbedder
from semantic_search.store import build_store, save_store


def main() -> int:
    try:
        documents = load_documents(DATA_FILE)
    except (OSError, ValueError) as exc:
        print(f"Erro ao ler {DATA_FILE}: {exc}", file=sys.stderr)
        return 1
    print(f"{len(documents)} documentos carregados de {DATA_FILE.name}")

    print(f"Carregando modelo {DEFAULT_MODEL_NAME} (o primeiro uso baixa ~470 MB)...")
    embedder = SentenceTransformerEmbedder(DEFAULT_MODEL_NAME)

    start = time.perf_counter()
    store = build_store(documents, embedder)
    elapsed = time.perf_counter() - start
    print(f"Embeddings gerados: {store.size} vetores x {embedder.dimension} dimensões em {elapsed:.1f}s")

    save_store(store, INDEX_DIR)
    print(f"Índice salvo em {INDEX_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
