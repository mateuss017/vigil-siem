"""Testes de segurança da entrada e de fluxo completo da API de eventos."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Event

# Textos hostis: tentativas clássicas de injeção de SQL e de XSS.
HOSTILE_TEXTS = [
    pytest.param("'; DROP TABLE events; --", id="sql-drop-table"),
    pytest.param("' OR '1'='1", id="sql-or-true"),
    pytest.param("1; DELETE FROM events", id="sql-delete"),
    pytest.param("<script>alert(1)</script>", id="xss-script"),
    pytest.param('<img src=x onerror="alert(1)">', id="xss-img"),
]

# Corpos com o formato errado. Todos devem ser recusados com 422.
WRONG_TYPE_BODIES = [
    pytest.param({"source": 123, "message": "login falhou"}, id="source-is-number"),
    pytest.param({"source": "firewall-01", "message": None}, id="message-is-null"),
    pytest.param({"source": ["firewall-01"], "message": "x"}, id="source-is-list"),
    pytest.param({"source": "firewall-01", "message": {"k": "v"}}, id="message-is-object"),
    pytest.param([], id="body-is-empty-list"),
    pytest.param("texto solto", id="body-is-string"),
    pytest.param(None, id="body-is-null"),
]


def _count_events(session_factory: sessionmaker[Session]) -> int:
    """Conta os eventos gravados. Falha se a tabela 'events' não existir mais."""
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Event)) or 0


@pytest.mark.parametrize("field", ["source", "message"])
@pytest.mark.parametrize("text", HOSTILE_TEXTS)
def test_hostile_text_is_stored_as_plain_text(
    client: TestClient,
    session_factory: sessionmaker[Session],
    field: str,
    text: str,
) -> None:
    """Texto de ataque deve ser gravado e devolvido como texto comum."""
    event = {"source": "firewall-01", "message": "login falhou"}
    event[field] = text

    response = client.post("/events", json=event)

    assert response.status_code == 201
    assert response.json()[field] == text
    # A tabela continua existindo e só tem o evento que enviamos.
    assert _count_events(session_factory) == 1
    assert client.get("/events").json()[0][field] == text


def test_accents_emojis_and_other_alphabets_survive_a_round_trip(
    client: TestClient,
) -> None:
    """Acentos, emojis e outros alfabetos não podem ser corrompidos."""
    # Escritos com códigos (\u...) para não depender da codificação do terminal.
    text = "a\u00e7\u00e3o \u26a0\ufe0f \u65e5\u672c\u8a9e \U0001f6a8"

    created = client.post("/events", json={"source": "firewall-01", "message": text})
    listed = client.get("/events").json()

    assert created.json()["message"] == text
    assert listed[0]["message"] == text


@pytest.mark.parametrize("payload", WRONG_TYPE_BODIES)
def test_wrong_json_types_are_rejected(
    client: TestClient,
    session_factory: sessionmaker[Session],
    payload: object,
) -> None:
    """Corpos com tipos ou formato errados devem receber 422 e não ser gravados."""
    response = client.post(
        "/events",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert _count_events(session_factory) == 0


def test_events_sent_through_the_api_are_listed_newest_first(
    client: TestClient,
) -> None:
    """Eventos gravados pela API devem voltar na listagem, do mais novo ao mais antigo."""
    for index in range(5):
        client.post(
            "/events", json={"source": "firewall-01", "message": f"evento-{index}"}
        )

    messages = [event["message"] for event in client.get("/events").json()]

    assert messages == [f"evento-{index}" for index in (4, 3, 2, 1, 0)]


def test_pages_cover_every_event_without_repeating_any(client: TestClient) -> None:
    """Ler a lista em páginas deve devolver todos os eventos, sem repetir nenhum."""
    for index in range(5):
        client.post(
            "/events", json={"source": "firewall-01", "message": f"evento-{index}"}
        )

    pages = [client.get(f"/events?limit=2&offset={offset}").json() for offset in (0, 2, 4)]
    messages = [event["message"] for page in pages for event in page]

    assert [len(page) for page in pages] == [2, 2, 1]
    assert messages == [f"evento-{index}" for index in (4, 3, 2, 1, 0)]


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_events_cannot_be_changed_or_deleted_through_the_api(
    client: TestClient, method: str
) -> None:
    """A API não deve oferecer meio de alterar ou apagar eventos."""
    response = client.request(method, "/events")

    assert response.status_code == 405


def test_single_event_route_does_not_exist_yet(client: TestClient) -> None:
    """Ainda não existe rota para um evento isolado (GET /events/{id})."""
    assert client.get("/events/1").status_code == 404


def test_responses_are_json_with_only_the_expected_fields(client: TestClient) -> None:
    """As respostas devem ser JSON e expor apenas os campos previstos."""
    created = client.post(
        "/events", json={"source": "firewall-01", "message": "login falhou"}
    )
    listed = client.get("/events")

    # Resposta JSON (e não HTML) impede que um texto com <script> seja executado
    # por um navegador que abra a resposta.
    assert created.headers["content-type"].startswith("application/json")
    assert listed.headers["content-type"].startswith("application/json")
    expected = {"id", "received_at", "source", "message"}
    assert set(created.json()) == expected
    assert set(listed.json()[0]) == expected