"""Classe base de todos os modelos (tabelas) do banco de dados."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Todos os modelos herdam desta classe. Ela guarda a lista de tabelas."""