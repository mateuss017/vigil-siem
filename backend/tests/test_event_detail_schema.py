"""Testes dos schemas de saída: EventRead (sem o original) e EventDetail (com ele)."""

from datetime import datetime, timezone

from app.models import Event
from app.schemas import EventDetail, EventRead, Severity

UTC = timezone.utc


def _model() -> Event:
    """Um evento como o banco o devolve: horários sem fuso e gravidade em texto."""
    return Event(
        id=1,
        received_at=datetime(2026, 11, 5, 12, 0),
        source="firewall-01",
        message="login falhou",
        timestamp=datetime(2026, 11, 5, 10, 0),
        hostname="web-01",
        event_type="login_failed",
        severity="high",
        source_ip="203.0.113.10",
        destination_ip="2001:db8::1",
        username="Admin",
        raw_event='{"source": "firewall-01"}',
    )


def test_event_read_has_no_raw_event_field() -> None:
    """O EventRead não deve ter o raw_event: ele pode ser grande demais para listas."""
    assert "raw_event" not in EventRead.model_fields


def test_event_detail_adds_only_the_raw_event_field() -> None:
    """O EventDetail é o EventRead mais o raw_event, e nada além disso."""
    extra = set(EventDetail.model_fields) - set(EventRead.model_fields)

    assert extra == {"raw_event"}


def test_event_read_is_built_from_the_database_model() -> None:
    """O EventRead lê o modelo do banco, restaura o UTC e não expõe o raw_event."""
    result = EventRead.model_validate(_model())

    assert result.severity == Severity.HIGH
    assert result.hostname == "web-01"
    assert result.received_at == datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    assert result.timestamp == datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
    assert "raw_event" not in result.model_dump()


def test_event_detail_is_built_from_the_database_model() -> None:
    """O EventDetail devolve também o original recebido."""
    result = EventDetail.model_validate(_model())

    assert result.raw_event == '{"source": "firewall-01"}'
    assert result.hostname == "web-01"


def test_event_detail_restores_utc_for_naive_datetimes() -> None:
    """O EventDetail herda a correção do fuso nos dois horários."""
    result = EventDetail(
        id=1,
        received_at=datetime(2026, 11, 5, 12, 0),
        source="firewall-01",
        message="login falhou",
        timestamp=datetime(2026, 11, 5, 10, 0),
    )

    assert result.received_at.tzinfo == UTC
    assert result.timestamp is not None
    assert result.timestamp.tzinfo == UTC