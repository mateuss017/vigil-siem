"""Conexão com o banco de dados e criação das tabelas."""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.base import Base


def _ensure_sqlite_directory(database_url: str) -> None:
    """Cria a pasta do arquivo SQLite, se ela ainda não existir."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    """Liga a verificação de chaves estrangeiras em cada conexão SQLite.

    O SQLite vem com essa verificação desligada, e o PRAGMA só vale para a
    conexão em que é executado. Por isso ele é aplicado a cada conexão nova.
    """
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _turn_on(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache
def get_engine() -> Engine:
    """Cria o 'motor' de conexão com o banco, uma única vez."""
    database_url = get_settings().database_url
    _ensure_sqlite_directory(database_url)
    engine = create_engine(database_url)
    enable_sqlite_foreign_keys(engine)
    return engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Devolve a fábrica de sessões (cada sessão é uma 'conversa' com o banco)."""
    return sessionmaker(bind=engine or get_engine())


def get_db() -> Iterator[Session]:
    """Entrega uma sessão para um único pedido da API e a fecha no final.

    Usada como dependência do FastAPI. O 'with' garante que a sessão seja
    fechada mesmo se ocorrer um erro durante o pedido. Quem grava os dados
    (o commit) é o próprio endpoint, e não esta função.
    """
    with get_session_factory()() as session:
        yield session


def init_db(engine: Engine | None = None) -> None:
    """Cria no banco as tabelas que ainda não existem."""
    # O import abaixo registra os modelos em Base. Fica aqui dentro para
    # evitar importação circular entre database e models.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine or get_engine())