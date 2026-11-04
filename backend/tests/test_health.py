"""Testes do endpoint de verificação de saúde da API."""

from fastapi.testclient import TestClient

from app.main import app

# O TestClient simula pedidos à API sem precisar subir o servidor.
client = TestClient(app)


def test_health_returns_ok() -> None:
    """O /health deve responder 200 com o corpo {"status": "ok"}."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}