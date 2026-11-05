"""Endpoints de eventos de segurança."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Event
from app.schemas import EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["events"])

# Quantos eventos a listagem devolve se o pedido não disser nada.
DEFAULT_LIMIT = 50
# Teto de eventos por consulta: protege a API e o banco de uma consulta gigante.
MAX_LIMIT = 200


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


@router.get("", response_model=list[EventRead])
def list_events(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Event]:
    """Lista eventos gravados, do mais novo para o mais antigo."""
    statement = (
        select(Event)
        # O id desempata eventos recebidos no mesmo instante, mantendo a
        # ordem sempre igual entre uma consulta e outra.
        .order_by(Event.received_at.desc(), Event.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())