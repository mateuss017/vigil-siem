"""Testes de endurecimento da entrada: entradas hostis que não podem causar erro 500."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Event

JSON_HEADERS = {"Content-Type": "application/json"}
# Maior inteiro que o SQLite guarda (2 elevado a 63, menos 1).
MAX_SQLITE_INTEGER = 2**63 - 1


def _body(**fields: object) -> bytes:
    """Monta o corpo de um evento válido, trocando ou acrescentando campos.

    O json.dumps escreve caracteres especiais como códigos (\\u0000, \\ud800),
    então o corpo enviado é só ASCII e não depende da codificação do terminal.
    """
    event = {"source": "firewall-01", "message": "login falhou", **fields}
    return json.dumps(event).encode("ascii")


def _count_events(session_factory: sessionmaker[Session]) -> int:
    """Conta os eventos gravados no banco temporário."""
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Event)) or 0


# --- Suspeita 1: offset grande demais para o banco ---


@pytest.mark.parametrize(
    "offset",
    [
        pytest.param(MAX_SQLITE_INTEGER + 1, id="one-above-the-limit"),
        pytest.param(99999999999999999999, id="huge-number"),
    ],
)
def test_offset_above_the_database_limit_is_rejected(
    lenient_client: TestClient, offset: int
) -> None:
    """Um offset que não cabe no banco deve receber 422, e não um erro 500."""
    response = lenient_client.get(f"/events?offset={offset}")

    assert response.status_code == 422


def test_the_largest_valid_offset_returns_an_empty_list(
    lenient_client: TestClient,
) -> None:
    """O maior offset que o banco aceita deve funcionar e devolver uma lista vazia."""
    response = lenient_client.get(f"/events?offset={MAX_SQLITE_INTEGER}")

    assert response.status_code == 200
    assert response.json() == []


# --- Suspeita 2: "surrogate" solto, que não pode ser escrito em UTF-8 ---


@pytest.mark.parametrize(
    "field", ["message", "source", "hostname", "event_type", "username"]
)
def test_lone_surrogate_is_rejected_in_every_text_field(
    lenient_client: TestClient,
    session_factory: sessionmaker[Session],
    field: str,
) -> None:
    """Um surrogate solto é JSON válido, mas não pode ser gravado: deve dar 422."""
    response = lenient_client.post(
        "/events", content=_body(**{field: "a\ud800b"}), headers=JSON_HEADERS
    )

    assert response.status_code == 422
    assert _count_events(session_factory) == 0


# --- Suspeita 3: caracteres de controle em message ---


@pytest.mark.parametrize(
    "char",
    [
        pytest.param("\u0000", id="null"),
        pytest.param("\u0001", id="start-of-heading"),
        pytest.param("\u001b", id="escape"),
        pytest.param("\u007f", id="delete"),
    ],
)
def test_control_characters_in_message_are_rejected(
    lenient_client: TestClient,
    session_factory: sessionmaker[Session],
    char: str,
) -> None:
    """Byte nulo, ESC e outros controles não são aceitos na mensagem."""
    response = lenient_client.post(
        "/events",
        content=_body(message=f"linha1{char}linha2"),
        headers=JSON_HEADERS,
    )

    assert response.status_code == 422
    assert _count_events(session_factory) == 0


@pytest.mark.parametrize(
    "separator",
    [
        pytest.param("\n", id="newline"),
        pytest.param("\t", id="tab"),
        pytest.param("\r\n", id="windows-newline"),
    ],
)
def test_line_breaks_and_tabs_in_message_are_kept(
    lenient_client: TestClient, separator: str
) -> None:
    """Mensagens de várias linhas são legítimas: quebras e tabulações devem passar."""
    message = f"linha1{separator}linha2"

    response = lenient_client.post(
        "/events", content=_body(message=message), headers=JSON_HEADERS
    )

    assert response.status_code == 201
    assert response.json()["message"] == message


# --- Suspeita 4: caracteres de controle em source ---


@pytest.mark.parametrize(
    "char",
    [
        pytest.param("\n", id="newline"),
        pytest.param("\t", id="tab"),
        pytest.param("\u0000", id="null"),
        pytest.param("\u001b", id="escape"),
    ],
)
def test_control_characters_in_source_are_rejected(
    lenient_client: TestClient,
    session_factory: sessionmaker[Session],
    char: str,
) -> None:
    """A origem é um campo curto: nenhum caractere de controle é aceito nela."""
    response = lenient_client.post(
        "/events", content=_body(source=f"web{char}01"), headers=JSON_HEADERS
    )

    assert response.status_code == 422
    assert _count_events(session_factory) == 0


# --- Suspeita 5: linha do banco com gravidade fora da lista ---


def test_listing_survives_a_row_with_an_unknown_severity(
    lenient_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Uma linha com gravidade inesperada não pode derrubar a listagem inteira."""
    with session_factory() as session:
        session.add(Event(source="firewall-01", message="valido", severity="high"))
        session.add(
            Event(source="firewall-01", message="editado a mao", severity="banana")
        )
        session.commit()

    response = lenient_client.get("/events")

    assert response.status_code == 200
    severities = {event["message"]: event["severity"] for event in response.json()}
    assert severities == {"valido": "high", "editado a mao": "banana"}


def test_detail_survives_a_row_with_an_unknown_severity(
    lenient_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """O evento isolado também deve ser lido, mesmo com gravidade inesperada."""
    with session_factory() as session:
        session.add(
            Event(source="firewall-01", message="editado a mao", severity="banana")
        )
        session.commit()

    response = lenient_client.get("/events/1")

    assert response.status_code == 200
    assert response.json()["severity"] == "banana"


# --- Só para documentar: chaves repetidas no JSON ---


def test_duplicate_json_keys_keep_the_last_value_and_the_original_text(
    lenient_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Com chave repetida vale o último valor, e o original guarda as duas."""
    body = b'{"source":"primeiro","source":"segundo","message":"login falhou"}'

    response = lenient_client.post("/events", content=body, headers=JSON_HEADERS)

    assert response.status_code == 201
    assert response.json()["source"] == "segundo"
    with session_factory() as session:
        saved = session.scalars(select(Event)).one()
    # O original mostra que alguém tentou enviar duas origens diferentes.
    assert saved.raw_event == body.decode("utf-8")