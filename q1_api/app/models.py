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


class BookBase(SQLModel):
    title: str = Field(min_length=1, max_length=200, index=True, description="Título do livro")
    author: str = Field(min_length=1, max_length=200, index=True, description="Autor do livro")
    published_date: date = Field(description="Data de publicação (ISO 8601: AAAA-MM-DD)")
    summary: str = Field(max_length=5000, description="Resumo do livro")


class Book(BookBase, table=True):
    # Atenção: modelos com table=True NÃO executam validação do Pydantic no __init__.
    # Por isso a validação acontece em BookCreate, antes de chegar aqui.
    id: int | None = Field(default=None, primary_key=True)


class BookCreate(BookBase):
    """Payload de criação. Adiciona regras de negócio além dos limites de tamanho."""

    @field_validator("title", "author")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        # TODO: remover espaços nas pontas e lançar ValueError se sobrar string vazia
        #       (ex.: "   " deve ser rejeitado com 422).
        return value

    @field_validator("published_date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        # TODO: lançar ValueError se a data for posterior a hoje.
        return value


class BookRead(BookBase):
    id: int
