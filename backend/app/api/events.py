"""Endpoints de eventos de segurança."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Event
from app.processing.normalizer import normalize_event
from app.schemas import EventCreate, EventDetail, EventRead

router = APIRouter(prefix="/events", tags=["events"])

# Quantos eventos a listagem devolve se o pedido não disser nada.
DEFAULT_LIMIT = 50
# Teto de eventos por consulta: protege a API e o banco de uma consulta gigante.
MAX_LIMIT = 200
# Maior número inteiro que o SQLite consegue guardar (2 elevado a 63, menos 1).
# Um id maior que isso nem chegaria ao banco: causaria um erro 500.
MAX_EVENT_ID = 2**63 - 1


async def get_raw_body(request: Request) -> bytes:
    """Entrega o corpo original do pedido, exatamente como chegou.

    O Starlette guarda o corpo depois da primeira leitura, então ler aqui não
    atrapalha a validação do evento, que também usa esse mesmo corpo.
    """
    return await request.body()


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    raw_body: Annotated[bytes, Depends(get_raw_body)],
    db: Annotated[Session, Depends(get_db)],
) -> Event:
    """Recebe um evento, valida, normaliza, grava no banco e devolve o evento criado."""
    # O normalizador monta o registro com os campos validados e guarda o corpo
    # original em raw_event. O id e o horário de recebimento são gerados aqui,
    # no servidor, e nunca vêm de fora.
    event = normalize_event(payload, raw_body)
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


@router.get("/{event_id}", response_model=EventDetail)
def get_event(
    event_id: Annotated[int, Path(ge=1, le=MAX_EVENT_ID)],
    db: Annotated[Session, Depends(get_db)],
) -> Event:
    """Devolve um evento isolado, com o original recebido (raw_event)."""
    # db.get busca direto pela chave primária (o id).
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )
    return event