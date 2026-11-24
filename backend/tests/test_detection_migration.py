"""Testes da migração que cria as tabelas de detecções."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from app.database.session import enable_sqlite_foreign_keys

# Pasta backend/, onde fica a pasta alembic/ com as migrações.
BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "6c8445d95a33"
DETECTION_TABLES = {"detections", "detection_events"}
DETECTION_COLUMNS = {
    "id",
    "rule_id",
    "severity",
    "group_key",
    "summary",
    "window_start",
    "window_end",
    "event_count",
    "created_at",
}
RECEIVED_AT = "2026-11-10 12:00:00.000000"


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Banco temporário em memória, com as chaves estrangeiras verificadas."""
    test_engine = create_engine("sqlite://", poolclass=StaticPool)
    enable_sqlite_foreign_keys(test_engine)
    yield test_engine
    test_engine.dispose()


def _alembic_config(connection: Connection) -> Config:
    """Monta a configuração do Alembic apontando para o banco temporário."""
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["connection"] = connection
    return config


def _insert_event(connection: Connection, message: str) -> None:
    """Grava um evento simples direto no banco, sem passar pela aplicação."""
    connection.execute(
        text(
            "INSERT INTO events (received_at, source, message) "
            "VALUES (:received_at, 'firewall-01', :message)"
        ),
        {"received_at": RECEIVED_AT, "message": message},
    )


def _insert_detection(connection: Connection) -> None:
    """Grava uma detecção mínima direto no banco."""
    connection.execute(
        text(
            "INSERT INTO detections (rule_id, severity, summary, event_count, created_at) "
            "VALUES ('failed_login_burst', 'high', 'resumo', 1, :created_at)"
        ),
        {"created_at": RECEIVED_AT},
    )


def _link_first_detection_to_first_event(connection: Connection) -> None:
    """Liga a detecção 1 ao evento 1, como prova."""
    connection.execute(
        text("INSERT INTO detection_events (detection_id, event_id) VALUES (1, 1)")
    )


def test_upgrade_creates_the_detection_tables(engine: Engine) -> None:
    """A migração deve criar as duas tabelas, com as colunas previstas."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")

    assert DETECTION_TABLES <= set(inspect(engine).get_table_names())
    columns = {column["name"] for column in inspect(engine).get_columns("detections")}
    assert columns == DETECTION_COLUMNS


def test_existing_events_survive_the_detections_migration(engine: Engine) -> None:
    """Um evento gravado antes da migração deve continuar igual depois dela."""
    with engine.begin() as connection:
        config = _alembic_config(connection)
        command.upgrade(config, PREVIOUS_REVISION)
        connection.execute(
            text(
                "INSERT INTO events "
                "(received_at, source, message, hostname, severity, raw_event) "
                "VALUES (:received_at, 'firewall-01', 'gravado antes', 'web-01', 'high', '{}')"
            ),
            {"received_at": RECEIVED_AT},
        )

        command.upgrade(config, "head")

        row = connection.execute(
            text(
                "SELECT source, message, received_at, hostname, severity, raw_event "
                "FROM events"
            )
        ).one()

    data = row._mapping
    assert data["source"] == "firewall-01"
    assert data["message"] == "gravado antes"
    assert data["received_at"] == RECEIVED_AT
    assert data["hostname"] == "web-01"
    assert data["severity"] == "high"
    assert data["raw_event"] == "{}"
    assert DETECTION_TABLES <= set(inspect(engine).get_table_names())


def test_downgrade_removes_only_the_detection_tables(engine: Engine) -> None:
    """Desfazer a migração apaga as tabelas de detecções e preserva os eventos."""
    with engine.begin() as connection:
        config = _alembic_config(connection)
        command.upgrade(config, "head")
        _insert_event(connection, "evento preservado")

        command.downgrade(config, PREVIOUS_REVISION)

        message = connection.execute(text("SELECT message FROM events")).scalar_one()
        tables = set(inspect(connection).get_table_names())

    assert message == "evento preservado"
    assert "events" in tables
    assert not DETECTION_TABLES & tables


def test_foreign_keys_are_enforced_after_the_migration(engine: Engine) -> None:
    """Uma prova que aponta para um evento inexistente deve ser recusada."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
        _insert_detection(connection)

        with pytest.raises(IntegrityError):
            connection.execute(
                text("INSERT INTO detection_events (detection_id, event_id) VALUES (1, 999)")
            )


def test_an_event_used_as_evidence_cannot_be_deleted(engine: Engine) -> None:
    """Um evento que serve de prova não pode ser apagado."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
        _insert_event(connection, "prova")
        _insert_detection(connection)
        _link_first_detection_to_first_event(connection)

        with pytest.raises(IntegrityError):
            connection.execute(text("DELETE FROM events WHERE id = 1"))


def test_deleting_a_detection_removes_its_links_but_not_the_event(
    engine: Engine,
) -> None:
    """Apagar uma detecção apaga as ligações dela, e o evento continua lá."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
        _insert_event(connection, "prova")
        _insert_detection(connection)
        _link_first_detection_to_first_event(connection)

        connection.execute(text("DELETE FROM detections WHERE id = 1"))

        links = connection.execute(
            text("SELECT COUNT(*) FROM detection_events")
        ).scalar_one()
        events = connection.execute(text("SELECT COUNT(*) FROM events")).scalar_one()

    assert links == 0
    assert events == 1