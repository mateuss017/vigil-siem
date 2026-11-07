"""Testes que mantêm o modelo do banco coerente com os schemas da API."""

import pytest

from app.models import Event
from app.schemas import Severity
from app.schemas.event import (
    EVENT_TYPE_MAX_LENGTH,
    HOSTNAME_MAX_LENGTH,
    IP_ADDRESS_MAX_LENGTH,
    SOURCE_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
)

COLUMNS = Event.__table__.c


@pytest.mark.parametrize(
    ("column", "limit"),
    [
        pytest.param("source", SOURCE_MAX_LENGTH, id="source"),
        pytest.param("hostname", HOSTNAME_MAX_LENGTH, id="hostname"),
        pytest.param("event_type", EVENT_TYPE_MAX_LENGTH, id="event_type"),
        pytest.param("source_ip", IP_ADDRESS_MAX_LENGTH, id="source_ip"),
        pytest.param("destination_ip", IP_ADDRESS_MAX_LENGTH, id="destination_ip"),
        pytest.param("username", USERNAME_MAX_LENGTH, id="username"),
    ],
)
def test_column_length_matches_the_schema_limit(column: str, limit: int) -> None:
    """Uma coluna de texto deve ter o mesmo tamanho que a API aceita."""
    assert COLUMNS[column].type.length == limit


def test_severity_column_fits_every_severity_level() -> None:
    """A coluna da gravidade deve comportar o nível mais longo da lista."""
    longest = max(len(level.value) for level in Severity)

    assert COLUMNS["severity"].type.length >= longest


@pytest.mark.parametrize(
    "column",
    [
        "timestamp",
        "hostname",
        "event_type",
        "severity",
        "source_ip",
        "destination_ip",
        "username",
        "raw_event",
    ],
)
def test_normalized_columns_are_optional(column: str) -> None:
    """Os campos novos devem aceitar vazio, para os eventos antigos continuarem válidos."""
    assert COLUMNS[column].nullable is True