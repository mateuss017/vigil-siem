"""Normalização: transforma um evento validado no registro que vai para o banco."""

from app.models import Event
from app.schemas import EventCreate


def decode_raw_event(raw_body: bytes) -> str:
    """Converte o corpo original do pedido em texto, sem nunca falhar.

    O corpo já foi lido como JSON antes de chegar aqui, então normalmente é
    UTF-8 válido. Se algum byte não for, ele é trocado pelo caractere de
    substituição (�) em vez de causar um erro: perder um byte é melhor do que
    perder o evento inteiro.
    """
    return raw_body.decode("utf-8", errors="replace")


def normalize_event(payload: EventCreate, raw_body: bytes) -> Event:
    """Monta o registro do banco a partir do evento validado e do corpo original.

    - Os campos validados (já em forma padrão pelo schema) são copiados.
    - A gravidade é guardada como texto simples ("high").
    - Nada é inventado: o que não veio no evento fica vazio, inclusive a gravidade.
    - O corpo original é guardado exatamente como chegou, em raw_event.
    - id e received_at ficam de fora: quem os gera é o servidor, ao gravar.
    """
    return Event(
        source=payload.source,
        message=payload.message,
        timestamp=payload.timestamp,
        hostname=payload.hostname,
        event_type=payload.event_type,
        severity=payload.severity.value if payload.severity is not None else None,
        source_ip=payload.source_ip,
        destination_ip=payload.destination_ip,
        username=payload.username,
        raw_event=decode_raw_event(raw_body),
    )