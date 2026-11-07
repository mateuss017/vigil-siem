"""Testes de integração: o POST /events grava os campos normalizados e o original."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Event

UTC = timezone.utc
JSON_HEADERS = {"Content-Type": "application/json"}

# Corpo propositalmente "bagunçado": espaços, quebras de linha, maiúsculas e
# campos fora de ordem. Serve para provar que o original é guardado intacto.
FULL_BODY = (
    b'{ "message": "login falhou para admin",\n'
    b'  "source": "firewall-01",\n'
    b'  "timestamp": "2026-11-05T10:00:00-03:00",\n'
    b'  "hostname": "  WEB-01 ",\n'
    b'  "event_type": "Login_Failed",\n'
    b'  "severity": "HIGH",\n'
    b'  "source_ip": " 203.0.113.10 ",\n'
    b'  "destination_ip": "2001:0DB8:0000:0000:0000:0000:0000:0001",\n'
    b'  "username": "Admin" }'
)
MINIMAL_BODY = b'{"source":"firewall-01","message":"login falhou"}'

NEW_FIELDS = [
    "timestamp",
    "hostname",
    "event_type",
    "severity",
    "source_ip",
    "destination_ip",
    "username",
]


def _json_body(**extra: object) -> bytes:
    """Monta o corpo de um evento válido, acrescentando os campos que o teste quiser."""
    event = {"source": "firewall-01", "message": "login falhou", **extra}
    return json.dumps(event).encode("utf-8")


def _saved_events(session_factory: sessionmaker[Session]) -> list[Event]:
    """Lê todos os eventos gravados no banco temporário."""
    with session_factory() as session:
        return list(session.scalars(select(Event)).all())


def test_full_event_is_stored_with_every_field(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Um evento completo deve ser gravado campo a campo, na forma normalizada."""
    response = client.post("/events", content=FULL_BODY, headers=JSON_HEADERS)

    assert response.status_code == 201
    body = response.json()
    assert body["hostname"] == "web-01"
    assert body["event_type"] == "login_failed"
    assert body["severity"] == "high"
    assert body["source_ip"] == "203.0.113.10"
    assert body["destination_ip"] == "2001:db8::1"
    assert body["username"] == "Admin"
    assert datetime.fromisoformat(body["timestamp"]) == datetime(
        2026, 11, 5, 13, 0, tzinfo=UTC
    )

    saved = _saved_events(session_factory)[0]
    assert saved.source == "firewall-01"
    assert saved.message == "login falhou para admin"
    assert saved.hostname == "web-01"
    assert saved.event_type == "login_failed"
    assert saved.severity == "high"
    assert saved.source_ip == "203.0.113.10"
    assert saved.destination_ip == "2001:db8::1"
    assert saved.username == "Admin"
    # O SQLite guarda o horário sem fuso: o valor gravado é o UTC (13:00).
    assert saved.timestamp is not None
    assert saved.timestamp.replace(tzinfo=UTC) == datetime(2026, 11, 5, 13, 0, tzinfo=UTC)


def test_event_with_only_required_fields_leaves_the_rest_empty(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Sem os campos novos, o evento é aceito e eles ficam vazios, sem valores inventados."""
    response = client.post("/events", content=MINIMAL_BODY, headers=JSON_HEADERS)

    assert response.status_code == 201
    body = response.json()
    saved = _saved_events(session_factory)[0]
    for field in NEW_FIELDS:
        assert body[field] is None
        assert getattr(saved, field) is None


def test_stored_raw_event_is_the_exact_body_that_was_sent(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """O original deve ser guardado exatamente como chegou, com espaços e maiúsculas."""
    client.post("/events", content=FULL_BODY, headers=JSON_HEADERS)

    saved = _saved_events(session_factory)[0]

    assert saved.raw_event == FULL_BODY.decode("utf-8")
    assert '"HIGH"' in saved.raw_event
    assert saved.severity == "high"


def test_responses_never_include_raw_event(client: TestClient) -> None:
    """Nem o POST nem a listagem devem devolver o raw_event."""
    created = client.post("/events", content=FULL_BODY, headers=JSON_HEADERS)
    listed = client.get("/events")

    assert "raw_event" not in created.json()
    assert all("raw_event" not in event for event in listed.json())


def test_client_cannot_send_raw_event(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Quem envia o evento não pode enviar o raw_event: ele é gerado pelo servidor."""
    response = client.post(
        "/events", content=_json_body(raw_event="forjado"), headers=JSON_HEADERS
    )

    assert response.status_code == 422
    assert _saved_events(session_factory) == []


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"severity": "alta"}, id="severity-not-in-the-list"),
        pytest.param({"source_ip": "999.1.1.1"}, id="source-ip-invalid"),
        pytest.param({"destination_ip": "abc"}, id="destination-ip-invalid"),
        pytest.param({"timestamp": "ontem"}, id="timestamp-not-a-date"),
        pytest.param({"timestamp": 1730000000}, id="timestamp-is-a-number"),
        pytest.param({"hostname": "web\n01"}, id="hostname-with-newline"),
        pytest.param({"hostname": ""}, id="hostname-empty"),
        pytest.param({"username": "a\x00b"}, id="username-with-null-byte"),
        pytest.param({"event_type": "x" * 101}, id="event-type-too-long"),
    ],
)
def test_invalid_new_fields_are_rejected_and_nothing_is_saved(
    client: TestClient,
    session_factory: sessionmaker[Session],
    extra: dict[str, object],
) -> None:
    """Campos novos inválidos recebem 422, e o evento não é gravado."""
    response = client.post("/events", content=_json_body(**extra), headers=JSON_HEADERS)

    assert response.status_code == 422
    assert _saved_events(session_factory) == []


def test_hostile_text_in_new_fields_is_stored_as_plain_text(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Texto de ataque nos campos novos é guardado como texto, e a tabela continua existindo."""
    body = _json_body(
        hostname="'; DROP TABLE events; --",
        username="<script>alert(1)</script>",
        event_type="<IMG SRC=x onerror=alert(1)>",
    )

    response = client.post("/events", content=body, headers=JSON_HEADERS)

    assert response.status_code == 201
    result = response.json()
    # Hostname e tipo de evento passam por minúsculas; o usuário não.
    assert result["hostname"] == "'; drop table events; --"
    assert result["username"] == "<script>alert(1)</script>"
    assert result["event_type"] == "<img src=x onerror=alert(1)>"
    assert len(_saved_events(session_factory)) == 1
    assert client.get("/events").status_code == 200


def test_non_ascii_text_in_new_fields_round_trips(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Acentos, emojis e outros alfabetos nos campos novos não podem ser corrompidos."""
    # Escritos com códigos (\u...) para não depender da codificação do terminal.
    username = "Jos\u00e9 \u65e5\u672c\u8a9e \U0001f6a8"

    response = client.post(
        "/events", content=_json_body(username=username), headers=JSON_HEADERS
    )

    assert response.json()["username"] == username
    assert _saved_events(session_factory)[0].username == username


def test_listing_returns_normalized_fields_newest_first(client: TestClient) -> None:
    """A listagem deve trazer os campos novos, do evento mais novo para o mais antigo."""
    client.post(
        "/events",
        content=_json_body(hostname="A-01", severity="low"),
        headers=JSON_HEADERS,
    )
    client.post(
        "/events",
        content=_json_body(hostname="B-02", severity="critical"),
        headers=JSON_HEADERS,
    )

    listed = client.get("/events").json()

    assert [event["hostname"] for event in listed] == ["b-02", "a-01"]
    assert [event["severity"] for event in listed] == ["critical", "low"]