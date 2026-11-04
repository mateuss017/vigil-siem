"""Ponto de entrada da API do Vigil SIEM."""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

# Cria a aplicação. O título e a versão aparecem na documentação
# automática, que o FastAPI gera em /docs.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de um SIEM construído do zero.",
    debug=settings.debug,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Informa que a aplicação está no ar."""
    return {"status": "ok"}