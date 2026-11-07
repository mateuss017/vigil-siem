"""Testes do normalizador de eventos."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Event
from app.processing.normalizer import decode_raw_event, normalize_event
from app.schemas import EventCreate, Severity

UTC = timezone.utc


def test_required_fields_are_copied_and_the_rest_stays_empty() -> None:
    """Só origem e mensagem: os outros campos ficam vazios, sem valores inventados."""
    payload = EventCreate(source="firewall-01", message="login falhou")

    event = normalize_event(payload, b"{}")

    assert isinstance(event, Event)
    assert event.source == "firewall-01"
    assert event.message == "login falhou"
    assert event.timestamp is None
    assert event.hostname is None
    assert event.event_type is None
    assert event.severity is None
    assert event.source_ip is None
    assert event.destination_ip is None
    assert event.username is None


def test_all_fields_are_copied_in_storage_form() -> None:
    """Todos os campos são copiados, e a gravidade vira texto simples."""
    payload = EventCreate(
        source="firewall-01",
        message="login falhou",
        timestamp="2026-11-05T10:00:00-03:00",
        hostname="  WEB-01 ",
        event_type="Login_Failed",
        severity="HIGH",
        source_ip="203.0.113.10",
        destination_ip="2001:0DB8:0000:0000:0000:0000:0000:0001",
        username="Admin",
    )

    event = normalize_event(payload, b"{}")

    # O schema já tinha deixado tudo em forma padrão; o normalizador só copia.
    assert event.timestamp == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)
    assert event.hostname == "web-01"
    assert event.event_type == "login_failed"
    assert event.severity == "high"
    assert type(event.severity) is str
    assert event.source_ip == "203.0.113.10"
    assert event.destination_ip == "2001:db8::1"
    assert event.username == "Admin"


def test_raw_event_keeps_the_original_text_exactly() -> None:
    """O original é guardado como chegou (espaços, quebras e ordem), sem normalização."""
    raw = (
        b'{  "message":"login falhou",\n "source" : "firewall-01" ,'
        b' "severity":"HIGH",  "hostname":"WEB-01" }'
    )
    payload = EventCreate.model_validate_json(raw)

    event = normalize_event(payload, raw)

    assert event.raw_event == raw.decode("utf-8")
    # O original continua com as maiúsculas; os campos normalizados, não.
    assert '"HIGH"' in event.raw_event
    assert event.severity == "high"
    assert '"WEB-01"' in event.raw_event
    assert event.hostname == "web-01"


def test_raw_event_keeps_non_ascii_characters() -> None:
    """Acentos, emojis e outros alfabetos do original não podem ser alterados."""
    # Escritos com códigos (\u...) para não depender da codificação do terminal.
    text = "conex\u00e3o bloqueada \u26a0\ufe0f \u65e5\u672c\u8a9e"
    raw = ('{"source":"firewall-01","message":"' + text + '"}').encode("utf-8")
    payload = EventCreate.model_validate_json(raw)

    event = normalize_event(payload, raw)

    assert text in event.raw_event
    assert event.message == text


def test_decode_raw_event_never_fails_on_invalid_utf8() -> None:
    """Bytes inválidos viram o caractere de substituição, e nunca um erro."""
    result = decode_raw_event(b'{"a": "\xff"}')

    assert result == '{"a": "\ufffd"}'
    assert type(result) is str


def test_empty_body_gives_empty_raw_event() -> None:
    """Um corpo vazio gera um texto vazio, sem erro."""
    assert decode_raw_event(b"") == ""


def test_server_generated_fields_are_left_empty() -> None:
    """id e received_at não são preenchidos aqui: são gerados ao gravar."""
    event = normalize_event(EventCreate(source="firewall-01", message="x"), b"{}")

    assert event.id is None
    assert event.received_at is None


def test_payload_is_not_modified() -> None:
    """O normalizador não deve alterar o evento recebido."""
    payload = EventCreate(
        source="firewall-01", message="login falhou", severity="HIGH", hostname="WEB-01"
    )
    before = payload.model_copy(deep=True)

    normalize_event(payload, b"{}")

    assert payload == before


@pytest.mark.parametrize("level", list(Severity), ids=lambda level: level.value)
def test_every_severity_level_is_stored_as_its_text(level: Severity) -> None:
    """Cada um dos cinco níveis é guardado como o seu texto."""
    payload = EventCreate(source="firewall-01", message="x", severity=level)

    event = normalize_event(payload, b"{}")

    assert event.severity == level.value


def test_normalized_event_can_be_saved_and_read(
    session_factory: sessionmaker[Session],
) -> None:
    """Um evento normalizado deve ser gravado no banco e lido de volta, campo a campo."""
    raw = (
        b'{"source":"firewall-01","message":"login falhou",'
        b'"timestamp":"2026-11-05T10:00:00-03:00","hostname":"WEB-01",'
        b'"event_type":"Login_Failed","severity":"HIGH",'
        b'"source_ip":"203.0.113.10","destination_ip":"2001:0DB8::1",'
        b'"username":"Admin"}'
    )
    event = normalize_event(EventCreate.model_validate_json(raw), raw)

    with session_factory() as session:
        session.add(event)
        session.commit()

    with session_factory() as session:
        saved = session.scalars(select(Event)).one()

    assert saved.id == 1
    assert saved.received_at is not None
    assert saved.source == "firewall-01"
    assert saved.message == "login falhou"
    # O SQLite guarda o horário sem fuso. O valor gravado é o horário já
    # convertido para UTC (13:00), e não o horário local original (10:00).
    assert saved.timestamp is not None
    assert saved.timestamp.replace(tzinfo=UTC) == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)
    assert saved.hostname == "web-01"
    assert saved.event_type == "login_failed"
    assert saved.severity == "high"
    assert saved.source_ip == "203.0.113.10"
    assert saved.destination_ip == "2001:db8::1"
    assert saved.username == "Admin"
    assert saved.raw_event == raw.decode("utf-8")