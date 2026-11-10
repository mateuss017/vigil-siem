"""Testes das funções auxiliares do tratamento de erros de validação."""

from app.core.errors import _safe_location, _safe_text


def test_safe_text_leaves_normal_text_unchanged() -> None:
    """Texto comum, com acentos, não deve ser alterado."""
    text = "campo normal a\u00e7\u00e3o"

    assert _safe_text(text) == text


def test_safe_text_turns_a_lone_surrogate_into_visible_text() -> None:
    """Um surrogate solto vira texto visível, que o UTF-8 consegue escrever."""
    result = _safe_text("a\ud800b")

    assert result == "a\\ud800b"
    assert result.encode("utf-8")


def test_safe_location_keeps_numbers_and_cleans_text() -> None:
    """Posições numéricas continuam números, e os textos são higienizados."""
    result = _safe_location(("body", 3, "x\ud800"))

    assert result == ["body", 3, "x\\ud800"]