"""Schemas (formatos de entrada e saída) da API."""

from app.schemas.event import EventCreate, EventDetail, EventRead, Severity

__all__ = ["EventCreate", "EventDetail", "EventRead", "Severity"]