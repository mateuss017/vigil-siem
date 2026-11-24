"""Testes do modelo de detecções e da ligação com os eventos que as provam."""

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import Engine, create_engine, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import (
    enable_sqlite_foreign_keys,
    get_session_factory,
    init_db,
)
from app.models import Detection, Event, detection_events

UTC = timezone.utc
WINDOW_START = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 11, 10, 12, 5, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Banco temporário em memória, com as chaves estrangeiras verificadas."""
    test_engine = create_engine("sqlite://", poolclass=StaticPool)
    enable_sqlite_foreign_keys(test_engine)
    init_db(test_engine)
    yield test_engine
    test_engine.dispose()


def _detection(**extra: object) -> Detection:
    """Cria uma detecção válida, trocando ou acrescentando os campos pedidos."""
    values: dict[str, object] = {
        "rule_id": "failed_login_burst",
        "severity": "high",
        "group_key": "203.0.113.10",
        "summary": "5 falhas de login do mesmo IP em 5 minutos",
        "event_count": 2,
        **extra,
    }
    return Detection(**values)


def _events(session: Session, count: int) -> list[Event]:
    """Grava eventos simples e devolve os objetos, já com o id preenchido."""
    events = [Event(source="firewall-01", message=f"falha {n}") for n in range(1, count + 1)]
    session.add_all(events)
    session.flush()
    return events


def test_detection_is_saved_with_its_evidence(engine: Engine) -> None:
    """Uma detecção deve ser gravada com os eventos de prova, lidos em ordem."""
    factory = get_session_factory(engine)

    with factory() as session:
        first, second = _events(session, 2)
        session.add(
            _detection(
                window_start=WINDOW_START,
                window_end=WINDOW_END,
                events=[second, first],
            )
        )
        session.commit()

    with factory() as session:
        detection = session.scalars(select(Detection)).one()

        assert detection.rule_id == "failed_login_burst"
        assert detection.severity == "high"
        assert detection.group_key == "203.0.113.10"
        assert detection.event_count == 2
        assert detection.created_at is not None
        # O SQLite devolve os horários sem fuso; os gravados foram em UTC.
        assert detection.window_start is not None
        assert detection.window_start.replace(tzinfo=UTC) == WINDOW_START
        assert detection.window_end is not None
        assert detection.window_end.replace(tzinfo=UTC) == WINDOW_END
        # As provas voltam ordenadas pelo id do evento.
        assert [event.message for event in detection.events] == ["falha 1", "falha 2"]


def test_detection_without_window_or_group_is_allowed(engine: Engine) -> None:
    """Regras que olham um evento isolado não têm janela nem grupo."""
    factory = get_session_factory(engine)

    with factory() as session:
        session.add(
            Detection(
                rule_id="critical_event",
                severity="medium",
                summary="evento de gravidade critica",
                event_count=1,
            )
        )
        session.commit()

    with factory() as session:
        detection = session.scalars(select(Detection)).one()

        assert detection.group_key is None
        assert detection.window_start is None
        assert detection.window_end is None


def test_evidence_must_point_to_an_existing_event(engine: Engine) -> None:
    """Uma prova apontando para um evento que não existe deve ser recusada."""
    factory = get_session_factory(engine)

    with factory() as session:
        detection = _detection()
        session.add(detection)
        session.flush()

        with pytest.raises(IntegrityError):
            session.execute(
                insert(detection_events).values(detection_id=detection.id, event_id=999)
            )


def test_the_same_event_cannot_be_linked_twice_to_one_detection(engine: Engine) -> None:
    """O par detecção e evento é único: não dá para repetir a mesma prova."""
    factory = get_session_factory(engine)

    with factory() as session:
        (event,) = _events(session, 1)
        detection = _detection(events=[event])
        session.add(detection)
        session.flush()

        with pytest.raises(IntegrityError):
            session.execute(
                insert(detection_events).values(
                    detection_id=detection.id, event_id=event.id
                )
            )


def test_deleting_a_detection_removes_its_links_but_not_the_events(
    engine: Engine,
) -> None:
    """Apagar uma detecção apaga as ligações dela e preserva os eventos."""
    factory = get_session_factory(engine)

    with factory() as session:
        first, second = _events(session, 2)
        session.add(_detection(events=[first, second]))
        session.commit()

    with factory() as session:
        session.execute(text("DELETE FROM detections"))
        session.commit()

    with factory() as session:
        links = session.scalar(select(func.count()).select_from(detection_events))
        events = session.scalar(select(func.count()).select_from(Event))

        assert links == 0
        assert events == 2


def test_an_event_that_is_evidence_cannot_be_deleted(engine: Engine) -> None:
    """Um evento que serve de prova de uma detecção não pode ser apagado."""
    factory = get_session_factory(engine)

    with factory() as session:
        (event,) = _events(session, 1)
        session.add(_detection(events=[event]))
        session.commit()
        event_id = event.id

    with factory() as session:
        with pytest.raises(IntegrityError):
            session.execute(text(f"DELETE FROM events WHERE id = {event_id}"))


def test_one_event_can_prove_more_than_one_detection(engine: Engine) -> None:
    """Um mesmo evento pode ser prova de várias detecções."""
    factory = get_session_factory(engine)

    with factory() as session:
        (shared,) = _events(session, 1)
        session.add_all(
            [
                _detection(rule_id="regra_a", events=[shared]),
                _detection(rule_id="regra_b", events=[shared]),
            ]
        )
        session.commit()

    with factory() as session:
        links = session.scalar(select(func.count()).select_from(detection_events))
        events = session.scalar(select(func.count()).select_from(Event))

        assert links == 2
        assert events == 1


def test_foreign_keys_are_enabled_on_new_connections(engine: Engine) -> None:
    """A verificação de chaves estrangeiras deve estar ligada na conexão."""
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1