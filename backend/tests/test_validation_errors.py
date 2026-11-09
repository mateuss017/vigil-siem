"""Testes do formato das respostas 422 (erros de validação)."""

import json

from fastapi.testclient import TestClient

JSON_HEADERS = {"Content-Type": "application/json"}


def _body(**fields: object) -> bytes:
    """Monta o corpo de um evento válido, trocando ou acrescentando campos (só ASCII)."""
    event = {"source": "firewall-01", "message": "login falhou", **fields}
    return json.dumps(event).encode("ascii")


def test_validation_error_has_only_location_message_and_type(
    lenient_client: TestClient,
) -> None:
    """Cada erro traz só onde, o quê e o tipo, e nunca o valor enviado."""
    response = lenient_client.post(
        "/events", content=_body(severity="alta"), headers=JSON_HEADERS
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors
    for error in errors:
        assert set(error) == {"loc", "msg", "type"}
    assert "severity" in errors[0]["loc"]


def test_hostile_input_is_not_echoed_back_in_the_error(
    lenient_client: TestClient,
) -> None:
    """O texto enviado, mesmo hostil, não deve voltar dentro da resposta de erro."""
    response = lenient_client.post(
        "/events",
        content=_body(source_ip="999.1.1.1<script>alert(1)</script>"),
        headers=JSON_HEADERS,
    )

    assert response.status_code == 422
    assert "<script>" not in response.text
    assert "999.1.1.1" not in response.text


def test_unknown_field_name_with_a_lone_surrogate_gets_422_not_500(
    lenient_client: TestClient,
) -> None:
    """O nome do campo desconhecido também é entrada do cliente e não pode quebrar a resposta."""
    response = lenient_client.post(
        "/events", content=_body(**{"campo\ud800": 1}), headers=JSON_HEADERS
    )

    assert response.status_code == 422
    # O surrogate aparece como texto visível (\ud800), e não derruba o servidor.
    assert "ud800" in response.text


def test_invalid_json_gets_a_clean_422(lenient_client: TestClient) -> None:
    """Um corpo que não é JSON recebe 422, no mesmo formato enxuto."""
    response = lenient_client.post(
        "/events", content=b"{isto nao e json", headers=JSON_HEADERS
    )

    assert response.status_code == 422
    for error in response.json()["detail"]:
        assert set(error) == {"loc", "msg", "type"}


def test_invalid_query_parameter_gets_a_clean_422(lenient_client: TestClient) -> None:
    """Erros nos parâmetros da URL também usam o formato enxuto."""
    response = lenient_client.get("/events?limit=abc")

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors
    assert set(errors[0]) == {"loc", "msg", "type"}
    assert "limit" in errors[0]["loc"]
    assert "abc" not in response.text