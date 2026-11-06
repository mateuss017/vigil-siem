"""Testes dos campos novos do schema de entrada dos eventos."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas import EventCreate, Severity
from app.schemas.event import (
    EVENT_TYPE_MAX_LENGTH,
    HOSTNAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
)

UTC = timezone.utc
TEXT_FIELDS = ["hostname", "event_type", "username"]
IP_FIELDS = ["source_ip", "destination_ip"]


def _event(**extra: object) -> EventCreate:
    """Cria um evento válido, acrescentando os campos que o teste quiser."""
    return EventCreate(source="firewall-01", message="login falhou", **extra)


def test_new_fields_are_optional() -> None:
    """Sem os campos novos, o evento continua válido e eles ficam vazios."""
    event = _event()

    assert event.timestamp is None
    assert event.hostname is None
    assert event.event_type is None
    assert event.severity is None
    assert event.source_ip is None
    assert event.destination_ip is None
    assert event.username is None


def test_explicit_null_is_treated_as_missing() -> None:
    """Enviar null equivale a não enviar o campo."""
    event = _event(
        timestamp=None,
        hostname=None,
        event_type=None,
        severity=None,
        source_ip=None,
        destination_ip=None,
        username=None,
    )

    assert event.severity is None
    assert event.hostname is None


def test_all_new_fields_are_accepted_and_normalized() -> None:
    """Todos os campos novos devem ser aceitos e vir na forma padrão."""
    event = _event(
        timestamp="2026-11-05T10:00:00-03:00",
        hostname="  WEB-01.Example.COM ",
        event_type="Login_Failed",
        severity="HIGH",
        source_ip=" 203.0.113.10 ",
        destination_ip="2001:0DB8:0000:0000:0000:0000:0000:0001",
        username="  Admin ",
    )

    assert event.timestamp == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)
    assert event.hostname == "web-01.example.com"
    assert event.event_type == "login_failed"
    assert event.severity == Severity.HIGH
    assert event.source_ip == "203.0.113.10"
    assert event.destination_ip == "2001:db8::1"
    assert event.username == "Admin"


def test_hostname_and_event_type_are_lowercased_and_stripped() -> None:
    """Hostname e tipo de evento ficam em minúsculas e sem espaços nas pontas."""
    event = _event(hostname="  SERVER-A  ", event_type="  Port_Scan ")

    assert event.hostname == "server-a"
    assert event.event_type == "port_scan"


def test_username_keeps_its_case() -> None:
    """O usuário não deve ser convertido para minúsculas."""
    assert _event(username="Administrator").username == "Administrator"


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        pytest.param("high", Severity.HIGH, id="lowercase"),
        pytest.param("HIGH", Severity.HIGH, id="uppercase"),
        pytest.param(" Medium ", Severity.MEDIUM, id="mixed-case-with-spaces"),
        pytest.param("CRITICAL", Severity.CRITICAL, id="critical"),
        pytest.param("informational", Severity.INFORMATIONAL, id="informational"),
        pytest.param("low", Severity.LOW, id="low"),
    ],
)
def test_severity_accepts_the_allowed_levels_in_any_case(
    sent: str, expected: Severity
) -> None:
    """Os cinco níveis são aceitos, com qualquer combinação de maiúsculas."""
    event = _event(severity=sent)

    assert event.severity == expected
    assert event.severity.value == expected.value


@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("alta", id="not-in-the-list"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
        pytest.param("urgent", id="other-word"),
        pytest.param(3, id="number"),
    ],
)
def test_invalid_severity_is_rejected(sent: object) -> None:
    """Gravidade fora da lista deve ser recusada."""
    with pytest.raises(ValidationError):
        _event(severity=sent)


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        pytest.param("203.0.113.10", "203.0.113.10", id="ipv4"),
        pytest.param(" 203.0.113.10 ", "203.0.113.10", id="ipv4-with-spaces"),
        pytest.param(
            "2001:0DB8:0000:0000:0000:0000:0000:0001", "2001:db8::1", id="ipv6-long"
        ),
        pytest.param("::1", "::1", id="ipv6-loopback"),
    ],
)
def test_valid_ip_addresses_are_written_in_canonical_form(
    sent: str, expected: str
) -> None:
    """IPs válidos (IPv4 e IPv6) são aceitos e escritos na forma padrão."""
    event = _event(source_ip=sent, destination_ip=sent)

    assert event.source_ip == expected
    assert event.destination_ip == expected


@pytest.mark.parametrize("field", IP_FIELDS)
@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("999.1.1.1", id="octet-above-255"),
        pytest.param("abc", id="not-an-ip"),
        pytest.param("1.2.3", id="missing-octet"),
        pytest.param("203.0.113.10/24", id="network-notation"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
        pytest.param("1" * 65, id="too-long"),
        pytest.param("203.0.113.10; DROP TABLE events", id="sql-text"),
        pytest.param("010.0.0.1", id="leading-zero"),
    ],
)
def test_invalid_ip_addresses_are_rejected(field: str, sent: str) -> None:
    """Endereços IP inválidos devem ser recusados, nos dois campos de IP."""
    with pytest.raises(ValidationError):
        _event(**{field: sent})


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        pytest.param(
            "2026-11-05T10:00:00-03:00",
            datetime(2026, 11, 5, 13, 0, tzinfo=UTC),
            id="offset-converted-to-utc",
        ),
        pytest.param(
            "2026-11-05T10:00:00Z",
            datetime(2026, 11, 5, 10, 0, tzinfo=UTC),
            id="z-suffix",
        ),
        pytest.param(
            "2026-11-05T10:00:00",
            datetime(2026, 11, 5, 10, 0, tzinfo=UTC),
            id="without-timezone-is-utc",
        ),
    ],
)
def test_timestamp_is_converted_to_utc(sent: str, expected: datetime) -> None:
    """O horário do evento deve ser convertido para UTC."""
    event = _event(timestamp=sent)

    assert event.timestamp == expected
    assert event.timestamp.utcoffset() == timedelta(0)


def test_timestamp_accepts_a_datetime_object() -> None:
    """Um objeto de data e hora com fuso também é aceito e convertido para UTC."""
    moment = datetime(2026, 11, 5, 10, 0, tzinfo=timezone(timedelta(hours=-3)))

    event = _event(timestamp=moment)

    assert event.timestamp == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)
    assert event.timestamp.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("2000-01-01T00:00:00Z", id="lower-bound"),
        pytest.param("2100-01-01T00:00:00Z", id="upper-bound"),
    ],
)
def test_timestamp_at_the_range_limits_is_accepted(sent: str) -> None:
    """Os limites da faixa aceita (anos 2000 e 2100) devem ser aceitos."""
    assert _event(timestamp=sent).timestamp is not None


@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("1999-12-31T23:59:59Z", id="before-the-range"),
        pytest.param("2100-01-01T00:00:01Z", id="after-the-range"),
        pytest.param("0001-01-01T00:00:00+14:00", id="overflow-low"),
        pytest.param("9999-12-31T23:59:59-14:00", id="overflow-high"),
        pytest.param("ontem", id="not-a-date"),
        pytest.param("", id="empty"),
        pytest.param(1730000000, id="unix-number"),
        pytest.param(True, id="boolean"),
    ],
)
def test_invalid_timestamp_is_rejected(sent: object) -> None:
    """Horários fora da faixa, em formato errado ou numéricos devem ser recusados."""
    with pytest.raises(ValidationError):
        _event(timestamp=sent)


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("a\nb", id="newline"),
        pytest.param("a\x00b", id="null-byte"),
        pytest.param("a\tb", id="tab"),
    ],
)
def test_control_characters_are_rejected(field: str, sent: str) -> None:
    """Quebras de linha e outros caracteres de controle devem ser recusados."""
    with pytest.raises(ValidationError):
        _event(**{field: sent})


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("sent", ["", "   "])
def test_blank_text_fields_are_rejected(field: str, sent: str) -> None:
    """Textos vazios ou só com espaços devem ser recusados."""
    with pytest.raises(ValidationError):
        _event(**{field: sent})


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        pytest.param("hostname", HOSTNAME_MAX_LENGTH, id="hostname"),
        pytest.param("event_type", EVENT_TYPE_MAX_LENGTH, id="event_type"),
        pytest.param("username", USERNAME_MAX_LENGTH, id="username"),
    ],
)
def test_text_fields_accept_the_limit_and_reject_one_more(
    field: str, limit: int
) -> None:
    """Cada campo aceita exatamente o seu tamanho máximo, e nada acima disso."""
    assert getattr(_event(**{field: "a" * limit}), field) == "a" * limit

    with pytest.raises(ValidationError):
        _event(**{field: "a" * (limit + 1)})