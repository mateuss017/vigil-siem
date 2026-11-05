"""Preparações (fixtures) compartilhadas pelos testes da API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import get_db, get_session_factory, init_db
from app.main import app


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    """Banco temporário em memória, descartado ao fim de cada teste."""
    # check_same_thread=False: a API roda em outra linha de execução do Python,
    # e o SQLite em memória, por padrão, recusa conexões usadas fora da linha
    # que as criou.
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    init_db(engine)
    yield get_session_factory(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """Cliente de testes da API, ligado ao banco temporário (nunca ao real)."""

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    # Troca, só durante o teste, a sessão do banco real pela do banco temporário.
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()