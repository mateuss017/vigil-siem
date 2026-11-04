"""Ambiente de execução das migrações do Alembic.

Em vez de ler o endereço do banco de um arquivo fixo, usa as mesmas
configurações da aplicação (variáveis de ambiente e .env).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import get_engine

# Importar os modelos registra as tabelas em Base.metadata, que é o que o
# Alembic compara com o banco para gerar migrações automaticamente.
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _run_migrations(connection: Connection) -> None:
    """Configura o contexto do Alembic e executa as migrações pendentes."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # O SQLite não altera tabelas como outros bancos; o modo "batch"
        # recria a tabela quando necessário, mantendo as migrações funcionais.
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem conectar ao banco."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa as migrações conectando ao banco."""
    # Os testes podem entregar uma conexão pronta (um banco temporário).
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_migrations(connection)
        return

    with get_engine().connect() as connection:
        _run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()