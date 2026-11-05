"""Testes do limite de tamanho do corpo dos pedidos."""

import json

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.limits import TOO_LARGE_DETAIL
from app.main import app
from app.models import Event

MAX_BODY_BYTES = get_settings().max_body_bytes
JSON_HEADERS = {"Content-Type": "application/json"}


def _count_events(session_factory: sessionmaker[Session]) -> int:
    """Conta os eventos gravados no banco temporário."""
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Event)) or 0


async def _post_in_chunks(chunks: list[bytes]) -> tuple[int, bytes]:
    """Envia um POST /events em pedaços, SEM o cabeçalho Content-Length.

    Fala direto com a aplicação, sem passar pelo cliente de testes, para
    simular um cliente que não declara o tamanho do que vai enviar.
    """
    pending = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> dict[str, object]:
        if pending:
            return pending.pop(0)
        return {"type": "http.disconnect"}

    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/events",
        "raw_path": b"/events",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)

    status_code = next(
        int(message["status"])  # type: ignore[arg-type]
        for message in sent
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")  # type: ignore[misc]
        for message in sent
        if message["type"] == "http.response.body"
    )
    return status_code, body


@pytest.mark.parametrize(
    ("size", "expected_status"),
    [
        # Exatamente no limite: o tamanho é aceito, mas o conteúdo não é um
        # JSON válido, então o erro esperado é 422 (e não 413).
        pytest.param(MAX_BODY_BYTES, 422, id="exactly-at-the-limit"),
        # Um byte acima do limite: recusado por tamanho.
        pytest.param(MAX_BODY_BYTES + 1, 413, id="one-byte-over-the-limit"),
    ],
)
def test_body_size_boundary(
    client: TestClient, size: int, expected_status: int
) -> None:
    """O limite deve valer exatamente: no limite passa, um byte acima é recusado."""
    response = client.post("/events", content=b"a" * size, headers=JSON_HEADERS)

    assert response.status_code == expected_status


def test_oversized_body_returns_json_error_and_saves_nothing(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Pedido grande demais: 413 com mensagem em JSON e nada gravado."""
    response = client.post(
        "/events", content=b"a" * (MAX_BODY_BYTES + 1), headers=JSON_HEADERS
    )

    assert response.status_code == 413
    assert response.json() == {"detail": TOO_LARGE_DETAIL}
    assert _count_events(session_factory) == 0


def test_oversized_chunked_body_is_rejected_without_content_length(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Sem Content-Length, os bytes recebidos são contados e o excesso é recusado."""
    chunks = [b"a" * MAX_BODY_BYTES, b"a"]

    status_code, body = anyio.run(_post_in_chunks, chunks)

    assert status_code == 413
    assert json.loads(body) == {"detail": TOO_LARGE_DETAIL}
    assert _count_events(session_factory) == 0


def test_small_chunked_body_is_still_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Um evento válido enviado em pedaços continua sendo aceito."""
    payload = json.dumps({"source": "firewall-01", "message": "login falhou"}).encode()
    middle = len(payload) // 2

    status_code, _ = anyio.run(_post_in_chunks, [payload[:middle], payload[middle:]])

    assert status_code == 201
    assert _count_events(session_factory) == 1