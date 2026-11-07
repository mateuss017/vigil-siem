"""Testes das migrações do Alembic."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database.base import Base

# Pasta backend/, onde fica a pasta alembic/ com as migrações.
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Banco SQLite temporário, só na memória, descartado ao fim de cada teste."""
    test_engine = create_engine("sqlite://", poolclass=StaticPool)
    yield test_engine
    test_engine.dispose()


def _alembic_config(connection: Connection) -> Config:
    """Monta a configuração do Alembic apontando para o banco temporário."""
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # O env.py usa esta conexão em vez de abrir a do banco real.
    config.attributes["connection"] = connection
    return config


def test_upgrade_creates_events_table(engine: Engine) -> None:
    """Aplicar as migrações num banco vazio deve criar a tabela 'events'."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")

    assert "events" in inspect(engine).get_table_names()


def test_migrations_match_models(engine: Engine) -> None:
    """Depois das migrações, o banco deve ser igual ao que os modelos descrevem."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
        differences = compare_metadata(
            MigrationContext.configure(connection), Base.metadata
        )

    assert differences == []


def test_downgrade_removes_events_table(engine: Engine) -> None:
    """Desfazer as migrações deve remover a tabela 'events'."""
    with engine.begin() as connection:
        config = _alembic_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "base")

    assert "events" not in inspect(engine).get_table_names()

FIRST_REVISION = "574c08f80b4d"
NORMALIZED_COLUMNS = [
    "timestamp",
    "hostname",
    "event_type",
    "severity",
    "source_ip",
    "destination_ip",
    "username",
    "raw_event",
]


def test_upgrade_adds_the_normalized_columns(engine: Engine) -> None:
    """A migração dos campos normalizados deve acrescentar as 8 colunas novas."""
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")

    columns = {column["name"] for column in inspect(engine).get_columns("events")}
    assert set(NORMALIZED_COLUMNS) <= columns


def test_existing_events_survive_the_normalized_fields_migration(
    engine: Engine,
) -> None:
    """Um evento gravado antes da migração deve continuar igual, com os campos novos vazios."""
    with engine.begin() as connection:
        config = _alembic_config(connection)
        command.upgrade(config, FIRST_REVISION)
        # Evento gravado com a estrutura ANTIGA, só com as 3 colunas de dados.
        connection.execute(
            text(
                "INSERT INTO events (received_at, source, message) VALUES "
                "('2026-11-05 12:00:00.000000', 'firewall-antigo', 'gravado antes da migracao')"
            )
        )

        command.upgrade(config, "head")

        columns = ", ".join(["source", "message", "received_at", *NORMALIZED_COLUMNS])
        row = connection.execute(text(f"SELECT {columns} FROM events")).one()

    data = row._mapping
    assert data["source"] == "firewall-antigo"
    assert data["message"] == "gravado antes da migracao"
    assert data["received_at"] == "2026-11-05 12:00:00.000000"
    # Nenhum valor foi inventado para os campos novos.
    assert all(data[column] is None for column in NORMALIZED_COLUMNS)


def test_downgrade_keeps_the_original_columns_and_their_data(engine: Engine) -> None:
    """Desfazer a migração remove só as colunas novas, e preserva os dados antigos."""
    with engine.begin() as connection:
        config = _alembic_config(connection)
        command.upgrade(config, "head")
        connection.execute(
            text(
                "INSERT INTO events (received_at, source, message, hostname, severity) VALUES "
                "('2026-11-05 12:00:00.000000', 'firewall-01', 'login falhou', 'web-01', 'high')"
            )
        )

        command.downgrade(config, FIRST_REVISION)

        row = connection.execute(
            text("SELECT source, message, received_at FROM events")
        ).one()
        columns = {column["name"] for column in inspect(connection).get_columns("events")}

    data = row._mapping
    assert data["source"] == "firewall-01"
    assert data["message"] == "login falhou"
    assert data["received_at"] == "2026-11-05 12:00:00.000000"
    assert columns == {"id", "received_at", "source", "message"}