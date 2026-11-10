"""Resposta padronizada para erros de validação (422)."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _safe_text(value: str) -> str:
    """Troca caracteres que o UTF-8 não consegue escrever por um código visível.

    Sem isso, um nome de campo com um "surrogate" solto (como U+D800) faria o
    próprio servidor falhar ao escrever a resposta de erro.
    """
    return value.encode("utf-8", errors="backslashreplace").decode("utf-8")


def _safe_location(location: tuple[int | str, ...]) -> list[int | str]:
    """Higieniza o caminho do erro, mantendo os números (posições) como números."""
    return [part if isinstance(part, int) else _safe_text(part) for part in location]


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Devolve 422 com onde, o quê e o tipo do erro, SEM repetir o texto enviado.

    O formato padrão do FastAPI inclui o valor que o cliente mandou (campo
    "input"). Não repeti-lo evita devolver ao cliente texto hostil, evita
    respostas enormes e evita o erro de codificação descrito acima.
    """
    errors = [
        {
            "loc": _safe_location(error["loc"]),
            "msg": _safe_text(error["msg"]),
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})