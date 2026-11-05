"""Testes da sessão de banco entregue a cada pedido da API."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.database.session as session_module
from app.database.session import get_db


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Banco temporário em memória, usado no lugar do banco real."""
    test_engine = create_engine("sqlite://", poolclass=StaticPool)
    # Faz get_db() usar o banco temporário, e nunca o data/vigil.db.
    monkeypatch.setattr(session_module, "get_engine", lambda: test_engine)
    yield test_engine
    test_engine.dispose()


def test_get_db_yields_a_working_session_and_closes_it(engine: Engine) -> None:
    """get_db deve entregar uma sessão funcional e fechá-la ao terminar."""
    generator = get_db()
    session = next(generator)

    assert isinstance(session, Session)
    assert session.execute(text("SELECT 1")).scalar() == 1
    # Depois de uma consulta, a sessão está com uma transação aberta.
    assert session.in_transaction()

    # Terminar o gerador equivale ao fim do pedido: a sessão deve ser fechada.
    with pytest.raises(StopIteration):
        next(generator)
    assert not session.in_transaction()


def test_get_db_closes_the_session_even_when_an_error_happens(engine: Engine) -> None:
    """Se o pedido falhar, a sessão deve ser fechada e o erro deve continuar."""
    generator = get_db()
    session = next(generator)
    session.execute(text("SELECT 1"))
    assert session.in_transaction()

    # Simula um erro acontecendo dentro do endpoint.
    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("falha simulada"))
    assert not session.in_transaction()


def test_each_request_gets_its_own_session(engine: Engine) -> None:
    """Dois pedidos diferentes não devem compartilhar a mesma sessão."""
    first_generator = get_db()
    second_generator = get_db()

    first_session = next(first_generator)
    second_session = next(second_generator)

    assert first_session is not second_session

    first_generator.close()
    second_generator.close()