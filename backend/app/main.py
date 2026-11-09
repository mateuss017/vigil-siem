"""Ponto de entrada da API do Vigil SIEM."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.events import router as events_router
from app.core.config import get_settings
from app.core.errors import validation_error_handler
from app.core.limits import MaxBodySizeMiddleware

settings = get_settings()

# Cria a aplicação. O título e a versão aparecem na documentação
# automática, que o FastAPI gera em /docs.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de um SIEM construído do zero.",
    debug=settings.debug,
)

# Recusa pedidos com corpo maior que o limite configurado (resposta 413).
app.add_middleware(MaxBodySizeMiddleware, max_body_bytes=settings.max_body_bytes)

# Os erros de validação (422) não repetem o texto enviado pelo cliente.
app.add_exception_handler(RequestValidationError, validation_error_handler)

# Registra os endpoints de eventos (POST e GET /events e GET /events/{id}).
app.include_router(events_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Informa que a aplicação está no ar."""
    return {"status": "ok"}