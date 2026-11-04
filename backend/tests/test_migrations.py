"""Testes das migrações do Alembic."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, Engine, create_engine, inspect
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