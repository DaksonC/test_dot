"""Vector store: construção do índice FAISS e persistência em disco.

Arquivos gravados no diretório do índice:
- index.faiss     vetores (IndexFlatIP)
- documents.json  documentos na MESMA ordem dos vetores (posição i = vetor i)
- meta.json       modelo usado, dimensão, quantidade e data de criação
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import faiss

from semantic_search.documents import Document, parse_documents
from semantic_search.embeddings import Embedder

INDEX_FILE = "index.faiss"
DOCUMENTS_FILE = "documents.json"
META_FILE = "meta.json"


class IndexNotFoundError(FileNotFoundError):
    """O índice ainda não foi construído."""


class IndexCorruptedError(ValueError):
    """Os arquivos do índice estão inconsistentes entre si."""


@dataclass
class VectorStore:
    index: faiss.Index
    documents: list[Document]
    model_name: str

    @property
    def size(self) -> int:
        return self.index.ntotal


def build_store(documents: list[Document], embedder: Embedder) -> VectorStore:
    """Gera os embeddings dos documentos e os adiciona a um IndexFlatIP.

    IndexFlatIP faz busca exata (força bruta) por produto interno. Com vetores
    normalizados, produto interno = similaridade de cosseno. Para poucos
    milhares de documentos é rápido e não exige treino, ao contrário de
    índices aproximados (IVF, HNSW), que valem a pena em milhões de vetores.
    """
    if not documents:
        raise ValueError("Não há documentos para indexar.")

    vectors = embedder.encode([doc.content_for_embedding() for doc in documents])
    if vectors.shape != (len(documents), embedder.dimension):
        raise ValueError(f"Embeddings com formato inesperado: {vectors.shape}")

    index = faiss.IndexFlatIP(embedder.dimension)
    index.add(vectors)
    return VectorStore(index=index, documents=list(documents), model_name=embedder.model_name)


def save_store(store: VectorStore, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    faiss.write_index(store.index, str(directory / INDEX_FILE))
    (directory / DOCUMENTS_FILE).write_text(
        json.dumps([doc.to_dict() for doc in store.documents], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta = {
        "model_name": store.model_name,
        "dimension": store.index.d,
        "num_documents": store.size,
        "metric": "inner_product (cosseno, vetores normalizados)",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_store(directory: Path) -> VectorStore:
    """Carrega o índice do disco, validando que os três arquivos são consistentes."""
    paths = [directory / name for name in (INDEX_FILE, DOCUMENTS_FILE, META_FILE)]
    if not all(path.exists() for path in paths):
        raise IndexNotFoundError(
            f"Índice não encontrado em {directory}. Rode: python -m semantic_search.build"
        )

    index = faiss.read_index(str(paths[0]))
    documents = parse_documents(json.loads(paths[1].read_text(encoding="utf-8")))
    meta = json.loads(paths[2].read_text(encoding="utf-8"))

    # O mapeamento vetor -> documento é posicional; se as contagens divergirem,
    # a busca devolveria documentos errados. Melhor falhar do que mentir.
    if not (index.ntotal == len(documents) == meta.get("num_documents")):
        raise IndexCorruptedError(
            f"Inconsistência: {index.ntotal} vetores, {len(documents)} documentos, "
            f"meta diz {meta.get('num_documents')}. Reconstrua o índice."
        )
    if index.d != meta.get("dimension"):
        raise IndexCorruptedError("Dimensão do índice difere do meta.json. Reconstrua o índice.")

    return VectorStore(index=index, documents=documents, model_name=meta["model_name"])
