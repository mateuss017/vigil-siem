"""Configurações da aplicação, lidas de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório. Este arquivo fica em backend/app/core/, então a raiz
# está três níveis acima. Assim o .env é encontrado de qualquer pasta.
BASE_DIR = Path(__file__).resolve().parents[3]

# Banco SQLite local, guardado em data/ na raiz do projeto (pasta ignorada pelo Git).
DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'data' / 'vigil.db').as_posix()}"

# Tamanho máximo do corpo de um pedido: 256 KiB. Folgado o bastante para uma
# mensagem de 10.000 caracteres mesmo que o cliente escreva cada emoji como
# código (\uXXXX), e pequeno o bastante para barrar pedidos gigantes.
DEFAULT_MAX_BODY_BYTES = 262_144


class Settings(BaseSettings):
    """Valores configuráveis da aplicação, com padrões seguros."""

    app_name: str = "Vigil SIEM"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    database_url: str = DEFAULT_DATABASE_URL
    # gt=0: o limite precisa ser um número positivo de bytes.
    max_body_bytes: int = Field(default=DEFAULT_MAX_BODY_BYTES, gt=0)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="VIGIL_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Devolve as configurações, criadas uma única vez e reaproveitadas."""
    return Settings()