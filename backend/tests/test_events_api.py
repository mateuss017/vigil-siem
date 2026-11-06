"""Testes de integração do endpoint POST /events."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Event
from app.schemas.event import MESSAGE_MAX_LENGTH, SOURCE_MAX_LENGTH

VALID_EVENT = {"source": "firewall-01", "message": "conexão bloqueada"}

INVALID_PAYLOADS = [
    pytest.param({"source": "firewall-01"}, id="missing-message"),
    pytest.param({"message": "login falhou"}, id="missing-source"),
    pytest.param({"source": "   ", "message": "login falhou"}, id="blank-source"),
    pytest.param({"source": "firewall-01", "message": ""}, id="empty-message"),
    pytest.param(
        {"source": "a" * (SOURCE_MAX_LENGTH + 1), "message": "login falhou"},
        id="source-too-long",
    ),
    pytest.param(
        {"source": "firewall-01", "message": "a" * (MESSAGE_MAX_LENGTH + 1)},
        id="message-too-long",
    ),
    pytest.param({**VALID_EVENT, "unknown_field": "x"}, id="unknown-field"),
]



def _saved_events(session_factory: sessionmaker[Session]) -> list[Event]:
    """Lê todos os eventos que estão gravados no banco temporário."""
    with session_factory() as session:
        return list(session.scalars(select(Event)).all())


def test_create_event_returns_201_and_the_saved_event(client: TestClient) -> None:
    """Um evento válido deve ser aceito (201) e devolvido com id e horário."""
    response = client.post("/events", json=VALID_EVENT)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["source"] == "firewall-01"
    assert body["message"] == "conexão bloqueada"
    # O horário de recebimento deve existir e ser uma data válida.
    assert datetime.fromisoformat(body["received_at"])


def test_created_event_is_saved_in_the_database(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """O evento aceito deve estar realmente gravado no banco."""
    client.post("/events", json=VALID_EVENT)

    events = _saved_events(session_factory)

    assert len(events) == 1
    assert events[0].source == "firewall-01"
    assert events[0].message == "conexão bloqueada"


def test_each_event_gets_a_different_id(client: TestClient) -> None:
    """Dois eventos enviados em seguida devem receber ids diferentes."""
    first = client.post("/events", json=VALID_EVENT).json()
    second = client.post("/events", json=VALID_EVENT).json()

    assert first["id"] != second["id"]


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_event_is_rejected_and_not_saved(
    client: TestClient,
    session_factory: sessionmaker[Session],
    payload: dict[str, str],
) -> None:
    """Eventos inválidos devem receber 422 e não podem ser gravados."""
    response = client.post("/events", json=payload)

    assert response.status_code == 422
    assert _saved_events(session_factory) == []


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"id": 999}, id="client-sets-id"),
        pytest.param({"received_at": "2020-01-01T00:00:00Z"}, id="client-sets-time"),
    ],
)
def test_client_cannot_set_server_generated_fields(
    client: TestClient,
    session_factory: sessionmaker[Session],
    extra: dict[str, object],
) -> None:
    """Quem envia o evento não pode escolher o próprio id nem o horário."""
    response = client.post("/events", json={**VALID_EVENT, **extra})

    assert response.status_code == 422
    assert _saved_events(session_factory) == []


def test_non_json_body_is_rejected(client: TestClient) -> None:
    """Um corpo que não é JSON válido deve receber 422."""
    response = client.post(
        "/events",
        content="isto não é json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422