"""Modelo da tabela de eventos de segurança."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    """Momento atual em UTC, usado como horário de recebimento do evento."""
    return datetime.now(timezone.utc)


class Event(Base):
    """Um evento recebido pelo SIEM.

    Versão mínima, só para validar a persistência. Os campos completos de
    normalização (hostname, IPs, usuário, severidade...) entram na Fase 5.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    source: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)