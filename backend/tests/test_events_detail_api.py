"""Testes de integração do endpoint GET /events/{id}."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

JSON_HEADERS = {"Content-Type": "application/json"}

BODY = (
    b'{ "source": "firewall-01",\n'
    b'  "message": "login falhou",\n'
    b'  "severity": "HIGH",\n'
    b'  "hostname": " WEB-01 " }'
)
MINIMAL_BODY = b'{"source":"firewall-01","message":"x"}'

EXPECTED_FIELDS = {
    "id",
    "received_at",
    "source",
    "message",
    "timestamp",
    "hostname",
    "event_type",
    "severity",
    "source_ip",
    "destination_ip",
    "username",
    "raw_event",
}

# Maior inteiro que o SQLite guarda (2 elevado a 63, menos 1).
MAX_SQLITE_ID = 9223372036854775807


def _post(client: TestClient, body: bytes) -> dict[str, object]:
    """Envia um evento e devolve a resposta já convertida em dicionário."""
    response = client.post("/events", content=body, headers=JSON_HEADERS)
    assert response.status_code == 201
    return response.json()


def test_detail_returns_the_event_with_the_original_body(client: TestClient) -> None:
    """O evento isolado deve trazer os campos normalizados e o original, intacto."""
    created = _post(client, BODY)

    response = client.get(f"/events/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["source"] == "firewall-01"
    assert body["severity"] == "high"
    assert body["hostname"] == "web-01"
    # O original continua com as maiúsculas e os espaços que chegaram.
    assert body["raw_event"] == BODY.decode("utf-8")


def test_detail_response_has_exactly_the_expected_fields(client: TestClient) -> None:
    """A resposta deve ter os 12 campos previstos, e nenhum a mais."""
    created = _post(client, BODY)

    response = client.get(f"/events/{created['id']}")

    assert response.headers["content-type"].startswith("application/json")
    assert set(response.json()) == EXPECTED_FIELDS


def test_detail_of_an_event_without_the_new_fields(client: TestClient) -> None:
    """Um evento simples volta com os campos novos vazios e o original preservado."""
    created = _post(client, MINIMAL_BODY)

    body = client.get(f"/events/{created['id']}").json()

    assert body["severity"] is None
    assert body["hostname"] is None
    assert body["timestamp"] is None
    assert body["raw_event"] == MINIMAL_BODY.decode("utf-8")


def test_detail_picks_the_requested_event(client: TestClient) -> None:
    """Com vários eventos gravados, o id pedido deve devolver exatamente aquele."""
    for index in range(3):
        _post(client, f'{{"source":"firewall-01","message":"evento-{index}"}}'.encode())

    body = client.get("/events/2").json()

    assert body["id"] == 2
    assert body["message"] == "evento-1"


def test_unknown_event_id_returns_404_with_a_message(client: TestClient) -> None:
    """Um id que não existe deve receber 404 e uma mensagem em JSON."""
    response = client.get("/events/12345")

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found."}


@pytest.mark.parametrize(
    "event_id",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative"),
        pytest.param("abc", id="not-a-number"),
        pytest.param("1.5", id="decimal"),
        pytest.param(str(MAX_SQLITE_ID + 1), id="one-above-the-sqlite-limit"),
        pytest.param("99999999999999999999", id="huge-number"),
    ],
)
def test_invalid_event_ids_are_rejected_with_422(
    client: TestClient, event_id: str
) -> None:
    """Ids inválidos devem receber 422, e nunca um erro 500."""
    response = client.get(f"/events/{event_id}")

    assert response.status_code == 422


def test_the_largest_valid_event_id_returns_404_not_an_error(client: TestClient) -> None:
    """O maior id que o SQLite aceita deve ser consultado normalmente (404, sem erro)."""
    response = client.get(f"/events/{MAX_SQLITE_ID}")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_a_single_event_cannot_be_changed_or_deleted(
    client: TestClient, method: str
) -> None:
    """Nem a rota do evento isolado permite alterar ou apagar eventos."""
    response = client.request(method, "/events/1")

    assert response.status_code == 405


def test_a_padded_body_does_not_make_the_listing_huge(client: TestClient) -> None:
    """Um corpo cheio de espaços só pesa no evento isolado, e nunca na listagem."""
    padding = 200_000
    padded = b'{"source":"firewall-01",' + b" " * padding + b'"message":"login falhou"}'
    assert len(padded) < get_settings().max_body_bytes

    created = client.post("/events", content=padded, headers=JSON_HEADERS)
    assert created.status_code == 201

    # A resposta do POST e a listagem continuam pequenas.
    assert len(created.content) < 5_000
    assert len(client.get("/events").content) < 5_000
    # O original, com todo o enchimento, só aparece no evento isolado.
    detail = client.get(f"/events/{created.json()['id']}").json()
    assert detail["raw_event"] == padded.decode("utf-8")
    assert len(detail["raw_event"]) > padding