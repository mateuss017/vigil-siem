"""Modelo da tabela de eventos de segurança."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    """Momento atual em UTC, usado como horário de recebimento do evento."""
    return datetime.now(timezone.utc)


class Event(Base):
    """Um evento de segurança recebido pelo SIEM.

    Os tamanhos das colunas de texto acompanham os limites dos schemas da API
    (app/schemas/event.py). Um teste confere que os dois continuam iguais.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Quando o evento CHEGOU ao SIEM (gerado pelo servidor).
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    source: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)

    # Campos normalizados. "Mapped[... | None]" faz a coluna aceitar valor vazio
    # (NULL), o que mantém válidos os eventos gravados antes destes campos existirem.
    # Quando o evento ACONTECEU na origem, em UTC.
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hostname: Mapped[str | None] = mapped_column(String(255))
    event_type: Mapped[str | None] = mapped_column(String(100))
    # Guardada como texto (ex.: "high"); a API só deixa entrar os 5 níveis permitidos.
    severity: Mapped[str | None] = mapped_column(String(20))
    # 64 e não 45: um IPv6 com identificador de interface (fe80::1%eth0) é válido
    # e mais longo, e o schema aceita até 64.
    source_ip: Mapped[str | None] = mapped_column(String(64))
    destination_ip: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(256))
    # O evento original, como chegou, antes da normalização.
    raw_event: Mapped[str | None] = mapped_column(Text)