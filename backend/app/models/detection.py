"""Modelo das detecções: o que as regras encontraram e os eventos que provam."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.database.base import Base
from app.models.event import Event

# Ligação entre detecções e os eventos que servem de prova. Um evento pode
# provar mais de uma detecção, e uma detecção tem vários eventos.
detection_events = Table(
    "detection_events",
    Base.metadata,
    # Apagar uma detecção apaga as suas ligações, mas nunca os eventos.
    Column(
        "detection_id",
        Integer,
        ForeignKey("detections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Um evento que serve de prova não pode ser apagado.
    Column(
        "event_id",
        Integer,
        ForeignKey("events.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Detection(Base):
    """Algo que uma regra encontrou nos eventos."""

    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Identificador estável da regra (ex.: "failed_login_burst").
    rule_id: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    # Quem ou o que a regra agrupou (ex.: o IP de origem). Vazio nas regras que
    # olham um evento isolado.
    group_key: Mapped[str | None] = mapped_column(String(255))
    # Descrição legível, escrita no momento da detecção, para o histórico
    # continuar claro mesmo se a regra mudar de nome ou de parâmetros.
    summary: Mapped[str] = mapped_column(Text)
    # Janela de tempo analisada. Vazia nas regras sem janela.
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    events: Mapped[list[Event]] = relationship(
        secondary=detection_events, order_by=Event.id
    )