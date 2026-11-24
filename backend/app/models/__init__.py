"""Modelos (tabelas) do banco de dados."""

from app.models.detection import Detection, detection_events
from app.models.event import Event

__all__ = ["Detection", "Event", "detection_events"]