"""Busca semântica de documentos com sentence-transformers + FAISS."""

from semantic_search.search import SearchResult, SemanticSearcher, search

__all__ = ["SearchResult", "SemanticSearcher", "search"]
