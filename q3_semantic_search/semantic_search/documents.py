"""Modelo de documento e carregamento do conjunto de dados em JSON."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    category: str
    text: str

    def content_for_embedding(self) -> str:
        """Texto que vira vetor: o título concentra o assunto, então entra junto."""
        return f"{self.title}. {self.text}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


_REQUIRED_FIELDS = ("id", "title", "category", "text")


def parse_documents(raw: list[dict]) -> list[Document]:
    """Valida e converte a lista crua do JSON. Falha cedo com mensagens claras."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("O arquivo de documentos deve conter uma lista não vazia.")

    documents: list[Document] = []
    seen_ids: set[str] = set()
    for position, item in enumerate(raw):
        missing = [f for f in _REQUIRED_FIELDS if not str(item.get(f, "")).strip()]
        if missing:
            raise ValueError(f"Documento na posição {position} sem os campos: {', '.join(missing)}")
        if item["id"] in seen_ids:
            raise ValueError(f"id duplicado: {item['id']!r}")
        seen_ids.add(item["id"])
        documents.append(Document(**{f: str(item[f]).strip() for f in _REQUIRED_FIELDS}))
    return documents


def load_documents(path: Path) -> list[Document]:
    with path.open(encoding="utf-8") as file:
        return parse_documents(json.load(file))
