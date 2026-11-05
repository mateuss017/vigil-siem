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

def test_max_body_bytes_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """O limite do corpo tem um padrão e pode ser alterado por variável de ambiente."""
    monkeypatch.delenv("VIGIL_MAX_BODY_BYTES", raising=False)
    assert Settings(_env_file=None).max_body_bytes == 262_144

    monkeypatch.setenv("VIGIL_MAX_BODY_BYTES", "1000")
    assert Settings(_env_file=None).max_body_bytes == 1000


@pytest.mark.parametrize("value", ["0", "-5"])
def test_max_body_bytes_must_be_positive(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Um limite zero ou negativo deve gerar erro de validação."""
    monkeypatch.setenv("VIGIL_MAX_BODY_BYTES", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)