"""Conexão com o banco de dados e criação das tabelas."""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.base import Base


def _ensure_sqlite_directory(database_url: str) -> None:
    """Cria a pasta do arquivo SQLite, se ela ainda não existir."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_engine() -> Engine:
    """Cria o 'motor' de conexão com o banco, uma única vez."""
    database_url = get_settings().database_url
    _ensure_sqlite_directory(database_url)
    return create_engine(database_url)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Devolve a fábrica de sessões (cada sessão é uma 'conversa' com o banco)."""
    return sessionmaker(bind=engine or get_engine())


def init_db(engine: Engine | None = None) -> None:
    """Cria no banco as tabelas que ainda não existem."""
    # O import abaixo registra os modelos em Base. Fica aqui dentro para
    # evitar importação circular entre database e models.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine or get_engine())