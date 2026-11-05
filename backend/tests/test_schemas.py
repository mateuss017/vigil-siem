"""Testes dos schemas de evento."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import Event
from app.schemas import EventCreate, EventRead
from app.schemas.event import MESSAGE_MAX_LENGTH, SOURCE_MAX_LENGTH


def test_valid_event_is_accepted() -> None:
    """Um evento com origem e mensagem válidas deve ser aceito."""
    event = EventCreate(source="firewall-01", message="conexão bloqueada")

    assert event.source == "firewall-01"
    assert event.message == "conexão bloqueada"


def test_whitespace_is_stripped() -> None:
    """Espaços no começo e no fim dos textos devem ser removidos."""
    event = EventCreate(source="  firewall-01  ", message="  login falhou \n")

    assert event.source == "firewall-01"
    assert event.message == "login falhou"


@pytest.mark.parametrize("field", ["source", "message"])
def test_missing_field_is_rejected(field: str) -> None:
    """Faltando um campo obrigatório, o evento deve ser recusado."""
    data = {"source": "firewall-01", "message": "login falhou"}
    del data[field]

    with pytest.raises(ValidationError):
        EventCreate(**data)


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_or_blank_text_is_rejected(value: str) -> None:
    """Textos vazios ou só com espaços devem ser recusados."""
    with pytest.raises(ValidationError):
        EventCreate(source=value, message="login falhou")
    with pytest.raises(ValidationError):
        EventCreate(source="firewall-01", message=value)


def test_text_longer_than_limit_is_rejected() -> None:
    """Textos acima do tamanho máximo devem ser recusados."""
    with pytest.raises(ValidationError):
        EventCreate(source="a" * (SOURCE_MAX_LENGTH + 1), message="login falhou")
    with pytest.raises(ValidationError):
        EventCreate(source="firewall-01", message="a" * (MESSAGE_MAX_LENGTH + 1))


def test_text_at_the_limit_is_accepted() -> None:
    """Textos exatamente no limite devem ser aceitos."""
    event = EventCreate(
        source="a" * SOURCE_MAX_LENGTH, message="a" * MESSAGE_MAX_LENGTH
    )

    assert len(event.source) == SOURCE_MAX_LENGTH
    assert len(event.message) == MESSAGE_MAX_LENGTH


def test_unknown_field_is_rejected() -> None:
    """Campos desconhecidos devem gerar erro, e não ser ignorados em silêncio."""
    with pytest.raises(ValidationError):
        EventCreate(source="firewall-01", message="login falhou", severity="alta")


def test_event_read_can_be_built_from_database_model() -> None:
    """O schema de saída deve conseguir ler um objeto do modelo do banco."""
    moment = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    model = Event(id=7, received_at=moment, source="firewall-01", message="login falhou")

    result = EventRead.model_validate(model)

    assert result.id == 7
    assert result.received_at == moment
    assert result.source == "firewall-01"
    assert result.message == "login falhou"