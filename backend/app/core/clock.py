"""Relógio da aplicação."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Momento atual, em UTC e com fuso."""
    return datetime.now(timezone.utc)