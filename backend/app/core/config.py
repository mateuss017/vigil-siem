"""Configurações da aplicação, lidas de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repositório. Este arquivo fica em backend/app/core/, então a raiz
# está três níveis acima. Assim o .env é encontrado de qualquer pasta.
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Valores configuráveis da aplicação, com padrões seguros."""

    app_name: str = "Vigil SIEM"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False

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