"""Endpoints de eventos de segurança."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Event
from app.schemas import EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Event:
    """Recebe um evento, valida, grava no banco e devolve o evento criado."""
    # Só source e message vêm de fora. O id e o horário de recebimento
    # são gerados aqui, no servidor.
    event = Event(source=payload.source, message=payload.message)
    db.add(event)
    # Este commit é o momento em que o evento passa a existir de verdade.
    db.commit()
    # Recarrega o evento do banco, já com o id e o received_at gerados.
    db.refresh(event)
    return event