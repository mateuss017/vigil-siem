"""Testes das configurações da aplicação."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem variáveis definidas, os valores padrão devem ser os seguros."""
    for name in ("VIGIL_APP_NAME", "VIGIL_ENVIRONMENT", "VIGIL_DEBUG"):
        monkeypatch.delenv(name, raising=False)

    # _env_file=None impede a leitura de um .env real durante o teste.
    settings = Settings(_env_file=None)

    assert settings.app_name == "Vigil SIEM"
    assert settings.environment == "development"
    assert settings.debug is False


def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Variáveis de ambiente devem sobrescrever os valores padrão."""
    monkeypatch.setenv("VIGIL_APP_NAME", "Vigil Teste")
    monkeypatch.setenv("VIGIL_ENVIRONMENT", "testing")
    monkeypatch.setenv("VIGIL_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Vigil Teste"
    assert settings.environment == "testing"
    assert settings.debug is True


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um ambiente fora da lista permitida deve gerar erro de validação."""
    monkeypatch.setenv("VIGIL_ENVIRONMENT", "banana")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)