"""Modelos de dados do domínio "livro".

Separamos os modelos por papel (padrão recomendado pelo SQLModel):
- BookBase:   campos comuns, sem id.
- Book:       tabela do banco (table=True).
- BookCreate: payload de entrada do POST, com validações extras.
- BookRead:   resposta da API, sempre com id.
"""

from datetime import date

from pydantic import field_validator
from sqlmodel import Field, SQLModel

BOOK_EXAMPLE = {
    "title": "O Senhor dos Anéis",
    "author": "J.R.R. Tolkien",
    "published_date": "1954-07-29",
    "summary": "Frodo parte em uma jornada para destruir o Um Anel.",
}


class BookBase(SQLModel):
    title: str = Field(
        min_length=1, max_length=200, index=True,
        description="Título do livro", schema_extra={"examples": [BOOK_EXAMPLE["title"]]},
    )
    author: str = Field(
        min_length=1, max_length=200, index=True,
        description="Autor do livro", schema_extra={"examples": [BOOK_EXAMPLE["author"]]},
    )
    published_date: date = Field(
        description="Data de publicação no formato ISO 8601 (AAAA-MM-DD)",
        schema_extra={"examples": [BOOK_EXAMPLE["published_date"]]},
    )
    summary: str = Field(
        max_length=5000,
        description="Resumo do livro", schema_extra={"examples": [BOOK_EXAMPLE["summary"]]},
    )


class Book(BookBase, table=True):
    # Atenção: modelos com table=True NÃO executam validação do Pydantic no __init__.
    # Por isso a validação acontece em BookCreate, antes de chegar aqui.
    id: int | None = Field(default=None, primary_key=True)


class BookCreate(BookBase):
    """Payload de criação. Adiciona regras de negócio além dos limites de tamanho."""

    model_config = {"json_schema_extra": {"examples": [BOOK_EXAMPLE]}}

    # mode="before" roda antes das restrições do Field (min_length), então
    # "   " vira "" e é barrado com uma mensagem clara, em vez de passar
    # pelo min_length=1 (que contaria os espaços).
    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_and_reject_blank(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("não pode ser vazio ou conter apenas espaços")
        return value

    @field_validator("published_date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("a data de publicação não pode estar no futuro")
        return value


class BookRead(BookBase):
    id: int

    model_config = {"json_schema_extra": {"examples": [{"id": 1, **BOOK_EXAMPLE}]}}
