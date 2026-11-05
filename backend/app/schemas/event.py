"""Schemas dos eventos: o que a API aceita receber e o que ela devolve."""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

# O limite da origem acompanha o tamanho da coluna no banco (String(100)).
SOURCE_MAX_LENGTH = 100
# A mensagem é um texto livre no banco; este limite protege contra eventos gigantes.
MESSAGE_MAX_LENGTH = 10_000

# Texto sem espaços nas pontas, com pelo menos 1 caractere e um tamanho máximo.
Source = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=SOURCE_MAX_LENGTH),
]
Message = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH),
]


class EventCreate(BaseModel):
    """Evento recebido pela API. Só estes dois campos são aceitos."""

    # extra="forbid": qualquer campo desconhecido gera erro, em vez de ser ignorado.
    model_config = ConfigDict(extra="forbid")

    source: Source
    message: Message


class EventRead(BaseModel):
    """Evento devolvido pela API, já com os dados gerados pelo banco."""

    # from_attributes=True: permite criar este schema a partir de um objeto do banco.
    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime
    source: str
    message: str

    @field_validator("received_at")
    @classmethod
    def _assume_utc_when_naive(cls, value: datetime) -> datetime:
        """Trata como UTC um horário sem fuso.

        O horário de recebimento é sempre gravado em UTC, mas o SQLite não
        guarda o fuso e o devolve "sem fuso". Aqui o fuso é restaurado, para a
        API nunca devolver um horário ambíguo.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value