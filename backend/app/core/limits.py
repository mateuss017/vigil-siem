"""Limite do tamanho do corpo dos pedidos HTTP."""

from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 413 significa "conteúdo grande demais".
HTTP_413_TOO_LARGE = 413
TOO_LARGE_DETAIL = "Request body too large."


class MaxBodySizeMiddleware:
    """Recusa pedidos cujo corpo ultrapasse um número máximo de bytes.

    Um middleware é um "porteiro": todo pedido passa por ele antes de chegar
    aos endpoints. A conferência é feita de duas formas:
    1. pelo tamanho que o cliente declara no cabeçalho Content-Length;
    2. contando os bytes que realmente chegam, caso o cliente não declare o
       tamanho (envio em pedaços) ou declare um valor falso.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Só pedidos HTTP interessam (há outros tipos, como o de inicialização).
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Conferência 1: o tamanho declarado já passa do limite? Então recusa
        # na hora, sem ler o corpo.
        declared_length = self._declared_length(scope)
        if declared_length is not None and declared_length > self.max_body_bytes:
            response = JSONResponse(
                {"detail": TOO_LARGE_DETAIL}, status_code=HTTP_413_TOO_LARGE
            )
            await response(scope, receive, send)
            return

        # Conferência 2: conta os bytes à medida que chegam.
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    # O endpoint nem chega a rodar: a leitura do corpo falha
                    # e o FastAPI transforma este erro em uma resposta 413.
                    raise HTTPException(
                        status_code=HTTP_413_TOO_LARGE, detail=TOO_LARGE_DETAIL
                    )
            return message

        await self.app(scope, limited_receive, send)

    @staticmethod
    def _declared_length(scope: Scope) -> int | None:
        """Lê o Content-Length do pedido, ou None se ausente ou inválido."""
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None