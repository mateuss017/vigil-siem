"""Schemas dos eventos: o que a API aceita receber e o que ela devolve."""

import ipaddress
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    field_validator,
)

# O limite da origem acompanha o tamanho da coluna no banco (String(100)).
SOURCE_MAX_LENGTH = 100
# A mensagem é um texto livre no banco; este limite protege contra eventos gigantes.
MESSAGE_MAX_LENGTH = 10_000
HOSTNAME_MAX_LENGTH = 255
EVENT_TYPE_MAX_LENGTH = 100
USERNAME_MAX_LENGTH = 256
# Um IPv6 escrito por extenso tem até 45 caracteres; 64 dá folga e barra textos enormes.
IP_ADDRESS_MAX_LENGTH = 64

# Faixa aceita para o horário do evento. Datas fora dela são quase sempre erro
# da fonte. Não se compara com o relógio atual de propósito: o relógio de quem
# envia pode estar um pouco adiantado ou atrasado.
MIN_TIMESTAMP = datetime(2000, 1, 1, tzinfo=timezone.utc)
MAX_TIMESTAMP = datetime(2100, 1, 1, tzinfo=timezone.utc)


class Severity(StrEnum):
    """Níveis de gravidade permitidos, do menos ao mais grave."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Caracteres de controle: quebras de linha, tabulação, nulo etc.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def _reject_control_characters(value: str) -> str:
    """Recusa quebras de linha e outros caracteres de controle no meio do texto.

    Em campos curtos (host, usuário, tipo), uma quebra de linha serviria para
    forjar linhas falsas em arquivos de log ("log injection").
    """
    if _CONTROL_CHARACTERS.search(value):
        raise ValueError("must not contain control characters")
    return value


def _canonical_ip_address(value: str) -> str:
    """Valida um endereço IPv4 ou IPv6 e o devolve na forma padrão."""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise ValueError("must be a valid IPv4 or IPv6 address") from None


def _require_text_or_datetime(value: object) -> object:
    """Aceita só texto ISO 8601 ou data e hora; recusa números (ex.: 1730000000)."""
    if isinstance(value, (str, datetime)):
        return value
    raise ValueError("must be an ISO 8601 date and time string")


def _to_utc_within_range(value: datetime) -> datetime:
    """Converte para UTC (horário sem fuso é tratado como UTC) e confere a faixa."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    try:
        value = value.astimezone(timezone.utc)
    except OverflowError:
        # Datas nos extremos do calendário podem estourar na conversão de fuso.
        raise ValueError("date and time out of range") from None
    if not MIN_TIMESTAMP <= value <= MAX_TIMESTAMP:
        raise ValueError("date and time must be between 2000 and 2100")
    return value


# Texto sem espaços nas pontas, com pelo menos 1 caractere e um tamanho máximo.
Source = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=SOURCE_MAX_LENGTH),
]
Message = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH),
]

# Campos novos. A ordem dos itens importa: primeiro a limpeza do texto
# (StringConstraints), depois a conferência (AfterValidator).
Hostname = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=HOSTNAME_MAX_LENGTH,
    ),
    AfterValidator(_reject_control_characters),
]
EventType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=EVENT_TYPE_MAX_LENGTH,
    ),
    AfterValidator(_reject_control_characters),
]
# O usuário NÃO vai para minúsculas: em alguns sistemas, maiúsculas e minúsculas
# são nomes diferentes.
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=USERNAME_MAX_LENGTH),
    AfterValidator(_reject_control_characters),
]
IpAddress = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=IP_ADDRESS_MAX_LENGTH),
    AfterValidator(_canonical_ip_address),
]
Timestamp = Annotated[
    datetime,
    BeforeValidator(_require_text_or_datetime),
    AfterValidator(_to_utc_within_range),
]


class EventCreate(BaseModel):
    """Evento recebido pela API. Só estes campos são aceitos."""

    # extra="forbid": qualquer campo desconhecido gera erro, em vez de ser ignorado.
    model_config = ConfigDict(extra="forbid")

    source: Source
    message: Message
    # Quando o evento aconteceu na origem (diferente de received_at, que é
    # quando chegou aqui).
    timestamp: Timestamp | None = None
    hostname: Hostname | None = None
    event_type: EventType | None = None
    severity: Severity | None = None
    source_ip: IpAddress | None = None
    destination_ip: IpAddress | None = None
    username: Username | None = None

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_ignores_case(cls, value: object) -> object:
        """Aceita "HIGH", "High" e " high " como o mesmo nível."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class EventRead(BaseModel):
    """Evento devolvido pela API, já com os dados gerados pelo banco."""

    # from_attributes=True: permite criar este schema a partir de um objeto do banco.
    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime
    source: str
    message: str

    @field_validator("received_at")
    @classmethod
    def _assume_utc_when_naive(cls, value: datetime) -> datetime:
        """Trata como UTC um horário sem fuso.

        O horário de recebimento é sempre gravado em UTC, mas o SQLite não
        guarda o fuso e o devolve "sem fuso". Aqui o fuso é restaurado, para a
        API nunca devolver um horário ambíguo.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value