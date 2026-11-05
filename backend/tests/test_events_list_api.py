"""Testes de integração do endpoint GET /events."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.events import DEFAULT_LIMIT, MAX_LIMIT
from app.models import Event

BASE_TIME = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def _insert_events(
    session_factory: sessionmaker[Session], moments: list[datetime]
) -> None:
    """Grava eventos direto no banco temporário, com os horários escolhidos."""
    with session_factory() as session:
        for index, moment in enumerate(moments):
            session.add(
                Event(source="teste", message=f"evento-{index}", received_at=moment)
            )
        session.commit()


def _messages(response_body: list[dict[str, object]]) -> list[object]:
    """Extrai só as mensagens da resposta, para facilitar a comparação."""
    return [event["message"] for event in response_body]


def test_empty_database_returns_empty_list(client: TestClient) -> None:
    """Sem nenhum evento gravado, a lista deve vir vazia, com status 200."""
    response = client.get("/events")

    assert response.status_code == 200
    assert response.json() == []


def test_events_are_listed_from_newest_to_oldest(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """A ordem deve seguir o horário de recebimento, e não a ordem de gravação."""
    # Horários fora de ordem de propósito: o id 2 é o evento mais novo.
    _insert_events(
        session_factory,
        [
            BASE_TIME,
            BASE_TIME + timedelta(minutes=2),
            BASE_TIME + timedelta(minutes=1),
        ],
    )

    response = client.get("/events")

    assert _messages(response.json()) == ["evento-1", "evento-2", "evento-0"]


def test_events_with_the_same_time_are_ordered_by_id(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Eventos do mesmo instante devem sair do id maior para o menor."""
    _insert_events(session_factory, [BASE_TIME, BASE_TIME, BASE_TIME])

    response = client.get("/events")

    assert [event["id"] for event in response.json()] == [3, 2, 1]


def test_default_limit_is_applied(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Sem o parâmetro limit, devem voltar no máximo DEFAULT_LIMIT eventos."""
    total = DEFAULT_LIMIT + 5
    _insert_events(
        session_factory, [BASE_TIME + timedelta(minutes=i) for i in range(total)]
    )

    response = client.get("/events")

    body = response.json()
    assert len(body) == DEFAULT_LIMIT
    # O primeiro da lista é o mais novo de todos.
    assert body[0]["message"] == f"evento-{total - 1}"


def test_limit_parameter_restricts_the_result(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """O parâmetro limit deve restringir a quantidade, mantendo os mais novos."""
    _insert_events(
        session_factory, [BASE_TIME + timedelta(minutes=i) for i in range(5)]
    )

    response = client.get("/events?limit=2")

    assert _messages(response.json()) == ["evento-4", "evento-3"]


def test_offset_parameter_returns_the_next_page(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """O parâmetro offset deve pular os primeiros eventos da lista."""
    _insert_events(
        session_factory, [BASE_TIME + timedelta(minutes=i) for i in range(5)]
    )

    response = client.get("/events?limit=2&offset=2")

    assert _messages(response.json()) == ["evento-2", "evento-1"]


def test_offset_beyond_the_end_returns_empty_list(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Pular mais eventos do que existem deve devolver uma lista vazia."""
    _insert_events(
        session_factory, [BASE_TIME + timedelta(minutes=i) for i in range(3)]
    )

    response = client.get("/events?offset=10")

    assert response.status_code == 200
    assert response.json() == []


def test_limit_at_the_maximum_is_accepted(client: TestClient) -> None:
    """O valor máximo permitido para limit deve ser aceito."""
    response = client.get(f"/events?limit={MAX_LIMIT}")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("limit=0", id="limit-zero"),
        pytest.param(f"limit={MAX_LIMIT + 1}", id="limit-above-maximum"),
        pytest.param("limit=-1", id="limit-negative"),
        pytest.param("limit=abc", id="limit-not-a-number"),
        pytest.param("offset=-1", id="offset-negative"),
    ],
)
def test_invalid_query_parameters_are_rejected(
    client: TestClient, query: str
) -> None:
    """Valores inválidos de limit ou offset devem receber 422."""
    response = client.get(f"/events?{query}")

    assert response.status_code == 422


def test_received_at_is_returned_with_utc_timezone(client: TestClient) -> None:
    """O horário listado deve trazer o fuso UTC, e não vir ambíguo."""
    client.post("/events", json={"source": "firewall-01", "message": "login falhou"})

    body = client.get("/events").json()

    received_at = datetime.fromisoformat(body[0]["received_at"])
    assert received_at.utcoffset() == timedelta(0)