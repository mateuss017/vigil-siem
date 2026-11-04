"""Testes da persistência: criação de tabelas, gravação e leitura de eventos."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.pool import StaticPool

from app.database.session import get_session_factory, init_db
from app.models import Event


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Banco SQLite temporário, só na memória, descartado ao fim de cada teste."""
    # StaticPool faz todas as conexões usarem o mesmo banco em memória.
    test_engine = create_engine("sqlite://", poolclass=StaticPool)
    init_db(test_engine)
    yield test_engine
    test_engine.dispose()


def test_init_db_creates_events_table(engine: Engine) -> None:
    """Depois de init_db, a tabela 'events' deve existir."""
    assert "events" in inspect(engine).get_table_names()


def test_event_can_be_saved_and_read(engine: Engine) -> None:
    """Um evento gravado deve poder ser lido de volta, com os mesmos valores."""
    factory = get_session_factory(engine)

    with factory() as session:
        session.add(Event(source="teste-unitario", message="tentativa de login falhou"))
        session.commit()

    with factory() as session:
        events = session.scalars(select(Event)).all()

    assert len(events) == 1
    assert events[0].source == "teste-unitario"
    assert events[0].message == "tentativa de login falhou"
    assert events[0].received_at is not None