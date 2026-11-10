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


# Todos os caracteres de controle: quebra de linha, tabulação, nulo, ESC etc.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
# Os mesmos, EXCETO tabulação (\x09), quebra de linha (\x0a) e retorno de
# carro (\x0d), que são legítimos em mensagens de várias linhas.
_CONTROL_CHARACTERS_EXCEPT_LINE_BREAKS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _reject_unencodable_text(value: str) -> str:
    """Recusa texto que não pode ser escrito em UTF-8.

    Um "surrogate" solto (como o U+D800 de um JSON) é aceito pelo Python, mas
    nenhum arquivo ou banco UTF-8 consegue guardá-lo: sem esta conferência,
    gravar o evento causaria um erro interno (500).
    """
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("must not contain invalid Unicode characters") from None
    return value


def _reject_control_characters(value: str) -> str:
    """Recusa quebras de linha e outros caracteres de controle no meio do texto.

    Em campos curtos (origem, host, usuário, tipo), uma quebra de linha serviria
    para forjar linhas falsas em arquivos de log ("log injection"), e um ESC
    poderia "desenhar" na tela de quem lê o log.
    """
    if _CONTROL_CHARACTERS.search(value):
        raise ValueError("must not contain control characters")
    return value


def _reject_control_characters_except_line_breaks(value: str) -> str:
    """Na mensagem, recusa os controles perigosos, mas aceita linhas e tabulações."""
    if _CONTROL_CHARACTERS_EXCEPT_LINE_BREAKS.search(value):
        raise ValueError("must not contain control characters other than line breaks and tabs")
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


# A ordem dos itens importa: primeiro a limpeza do texto (StringConstraints),
# depois as conferências (AfterValidator), na ordem em que aparecem.
Source = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=SOURCE_MAX_LENGTH),
    AfterValidator(_reject_unencodable_text),
    AfterValidator(_reject_control_characters),
]
Message = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH),
    AfterValidator(_reject_unencodable_text),
    AfterValidator(_reject_control_characters_except_line_breaks),
]
Hostname = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=HOSTNAME_MAX_LENGTH,
    ),
    AfterValidator(_reject_unencodable_text),
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
    AfterValidator(_reject_unencodable_text),
    AfterValidator(_reject_control_characters),
]
# O usuário NÃO vai para minúsculas: em alguns sistemas, maiúsculas e minúsculas
# são nomes diferentes.
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=USERNAME_MAX_LENGTH),
    AfterValidator(_reject_unencodable_text),
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
    # Campos normalizados. Vazios (null) em eventos gravados sem eles.
    timestamp: datetime | None = None
    hostname: str | None = None
    event_type: str | None = None
    # Na SAÍDA a gravidade é texto comum, e não a lista fechada (Severity): uma
    # linha com valor inesperado (por exemplo, editada à mão no banco) não deve
    # derrubar a listagem inteira. Na ENTRADA a validação continua rígida: só os
    # 5 níveis do Severity são gravados.
    severity: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    # O raw_event NÃO está aqui de propósito: só o EventDetail o devolve.

    @field_validator("received_at", "timestamp")
    @classmethod
    def _assume_utc_when_naive(cls, value: datetime | None) -> datetime | None:
        """Trata como UTC um horário sem fuso.

        Os horários são sempre gravados em UTC, mas o SQLite não guarda o fuso
        e os devolve "sem fuso". Aqui o fuso é restaurado, para a API nunca
        devolver um horário ambíguo.
        """
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class EventDetail(EventRead):
    """Evento isolado, com o original recebido (raw_event).

    O raw_event pode ser grande (até o tamanho máximo do pedido), por isso só
    aparece quando UM evento é consultado, nunca em listas.
    """

    raw_event: str | None = None