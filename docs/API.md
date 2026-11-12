# API do Vigil SIEM

Referência dos endpoints da API. Este documento descreve apenas o que está **implementado e verificado** (por testes automatizados e por demonstrações manuais com o servidor real). O que ainda não existe está na seção [Não implementado](#não-implementado).

> **Aviso:** a API **não tem autenticação**. Qualquer programa que consiga acessar o servidor pode gravar e ler eventos. Use somente em ambiente local, com o servidor escutando em `127.0.0.1`. Veja o [SECURITY.md](../SECURITY.md).

## Visão geral

| Endpoint | Função | Situação |
|---|---|---|
| `GET /health` | Informa que a aplicação está no ar | Implementado |
| `POST /events` | Recebe, normaliza e grava um evento | Implementado |
| `GET /events` | Lista os eventos gravados | Implementado |
| `GET /events/{event_id}` | Consulta um evento isolado, com o original recebido | Implementado |
| `PUT`, `PATCH`, `DELETE` | Alteração e remoção de eventos | Não implementado, de propósito (resposta 405) |

## Como acessar

Com o servidor no ar (veja o [README](../README.md)), a API responde em `http://127.0.0.1:8000`. A documentação interativa gerada pelo FastAPI fica em `http://127.0.0.1:8000/docs`.

O banco de dados precisa ter sido criado antes com `python -m alembic upgrade head` (dentro de `backend/`). A aplicação **não** cria o banco ao iniciar. Detalhes em [DATABASE.md](DATABASE.md).

## Convenções

- Corpo dos pedidos e das respostas em **JSON**, com codificação **UTF-8**. Envie o cabeçalho `Content-Type: application/json`.
- Horários em **UTC**, no formato ISO 8601 com sufixo `Z` (por exemplo, `2026-11-05T13:00:00Z`).
- O `id`, o `received_at` e o `raw_event` são gerados pelo **servidor**. Quem envia o evento não pode escolhê-los.
- Eventos **não podem ser alterados nem apagados** pela API.

## Campos do evento

### Campos aceitos no `POST /events`

| Campo | Obrigatório | Regras e normalização |
|---|---|---|
| `source` | Sim | De 1 a 100 caracteres. Espaços das pontas são removidos. Não aceita caracteres de controle (quebra de linha, tabulação, byte nulo etc.). Identifica a origem do evento. |
| `message` | Sim | De 1 a 10.000 caracteres. Espaços das pontas são removidos. Aceita quebras de linha e tabulações (mensagens de várias linhas), mas recusa os demais caracteres de controle. |
| `timestamp` | Não | Quando o evento **aconteceu** na origem. Texto ISO 8601. Convertido para UTC; sem fuso, é tratado como UTC. Precisa estar entre `2000-01-01` e `2100-01-01` (UTC). Números (como `1730000000`) são recusados. |
| `hostname` | Não | De 1 a 255 caracteres. Espaços das pontas removidos e texto convertido para **minúsculas**. Sem caracteres de controle. |
| `event_type` | Não | De 1 a 100 caracteres. Espaços das pontas removidos e texto convertido para **minúsculas**. Sem caracteres de controle. |
| `severity` | Não | Um dos cinco níveis: `informational`, `low`, `medium`, `high`, `critical`. Maiúsculas e espaços nas pontas são aceitos e normalizados. |
| `source_ip` | Não | Endereço IPv4 ou IPv6 (até 64 caracteres). Escrito na forma padrão, por exemplo `2001:0DB8:0:0:0:0:0:1` vira `2001:db8::1`. Recusa máscaras (`/24`), zeros à esquerda (`010.0.0.1`) e texto que não é endereço. |
| `destination_ip` | Não | Mesmas regras do `source_ip`. |
| `username` | Não | De 1 a 256 caracteres. Espaços das pontas removidos. **Mantém** maiúsculas e minúsculas. Sem caracteres de controle. |

Regras gerais:

- Campo opcional ausente, ou enviado como `null`, fica **vazio**. Nenhum valor é inventado (por exemplo, sem `severity` o campo fica vazio).
- Campo opcional enviado como texto vazio ou só com espaços é **recusado** (422).
- Campos **desconhecidos** são recusados, incluindo `id`, `received_at` e `raw_event`.
- Valores de tipo errado (número, lista, objeto) são recusados.
- Texto com caracteres Unicode inválidos (como um "surrogate" solto, `\ud800` em JSON) é recusado, pois não pode ser guardado em UTF-8.
- O corpo inteiro do pedido não pode passar de **262.144 bytes** (256 KiB), configurável por `VIGIL_MAX_BODY_BYTES`.
- Se uma chave se repetir no JSON, vale o **último** valor. O `raw_event` guarda o texto original, com as duas.

### Campos devolvidos

Além dos campos acima, a resposta traz:

| Campo | Onde aparece | Significado |
|---|---|---|
| `id` | Todas as respostas | Número do evento, gerado pelo banco |
| `received_at` | Todas as respostas | Quando o evento **chegou** ao SIEM (UTC, gerado pelo servidor) |
| `raw_event` | Só em `GET /events/{event_id}` | O corpo do pedido **exatamente como chegou**, antes da normalização (espaços, maiúsculas e ordem dos campos preservados). Bytes que não sejam UTF-8 válido são trocados pelo caractere de substituição do Unicode (U+FFFD). |

O `raw_event` fica fora do `POST` e da listagem de propósito: ele pode ser grande (até o limite de tamanho do pedido), e uma lista com muitos eventos ficaria enorme.

## POST /events

Recebe um evento, valida, normaliza, grava no banco e devolve o evento criado.

### Exemplo (PowerShell)

```powershell
$evento = @{
    source = "firewall-01"
    message = "login falhou para o usuario admin"
    hostname = "WEB-01.Example.COM"
    severity = "HIGH"
    source_ip = "203.0.113.10"
} | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($evento)
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/events -ContentType "application/json" -Body $bytes
```

O texto é convertido em bytes UTF-8 antes do envio porque o Windows PowerShell 5.1 pode corromper acentos ao enviar texto direto.

### Resposta (201)

```json
{
  "id": 1,
  "received_at": "2026-11-10T20:04:41.053869Z",
  "source": "firewall-01",
  "message": "login falhou para o usuario admin",
  "timestamp": null,
  "hostname": "web-01.example.com",
  "event_type": null,
  "severity": "high",
  "source_ip": "203.0.113.10",
  "destination_ip": null,
  "username": null
}
```

Os valores são ilustrativos; o formato foi conferido nos testes e na demonstração manual.

### Erros

| Código | Quando acontece |
|---|---|
| 413 | O corpo do pedido passa de 262.144 bytes. A resposta é `{"detail": "Request body too large."}` e nada é gravado. |
| 422 | O corpo não é um JSON válido ou algum campo não respeita as regras. Nada é gravado. Formato em [Formato dos erros de validação](#formato-dos-erros-de-validação). |

## GET /events

Lista os eventos gravados, do **mais novo para o mais antigo** (pelo `received_at`). Eventos recebidos no mesmo instante são ordenados pelo `id`, do maior para o menor, para que a ordem seja sempre a mesma.

### Parâmetros de consulta

| Parâmetro | Tipo | Padrão | Regras |
|---|---|---|---|
| `limit` | inteiro | 50 | De 1 a 200. Quantidade máxima de eventos devolvidos. |
| `offset` | inteiro | 0 | De 0 a 9.223.372.036.854.775.807. Quantidade de eventos a pular, para ler a lista em páginas. |

### Resposta (200)

Uma lista de eventos, cada um com 11 campos: `id`, `received_at`, `source`, `message`, `timestamp`, `hostname`, `event_type`, `severity`, `source_ip`, `destination_ip` e `username`. Campos que não foram informados vêm como `null`. Se não houver eventos, a lista vem vazia (`[]`). A resposta **não** traz o total de eventos nem o `raw_event`.

### Exemplos (PowerShell)

```powershell
# Os 50 eventos mais recentes (padrão)
$eventos = Invoke-RestMethod http://127.0.0.1:8000/events
$eventos.Count

# Segunda página, com 2 eventos por página
Invoke-RestMethod "http://127.0.0.1:8000/events?limit=2&offset=2"
```

No Windows PowerShell 5.1, guarde o resultado em uma variável antes de contar. Escrever `@(Invoke-RestMethod ...).Count` devolve sempre 1, porque a lista chega embrulhada em um único objeto.

### Erros

| Código | Quando acontece |
|---|---|
| 422 | `limit` fora do intervalo de 1 a 200, `offset` negativo ou acima do máximo, ou valores que não são números. |

## GET /events/{event_id}

Devolve **um** evento, com todos os campos e o `raw_event`.

### Exemplo (PowerShell)

```powershell
$resposta = Invoke-WebRequest http://127.0.0.1:8000/events/1 -UseBasicParsing
$evento = [System.Text.Encoding]::UTF8.GetString($resposta.RawContentStream.ToArray()) | ConvertFrom-Json
$evento.raw_event
```

A resposta é decodificada como UTF-8 de forma explícita porque o Windows PowerShell 5.1 pode exibir acentos errados na tela.

### Resposta (200)

Os 11 campos da listagem mais o `raw_event`, 12 no total.

### Erros

| Código | Quando acontece |
|---|---|
| 404 | Não existe evento com esse `id`. A resposta é `{"detail": "Event not found."}`. |
| 422 | O `id` não é um número inteiro, é menor que 1 ou maior que 9.223.372.036.854.775.807. |

## Formato dos erros de validação

Os erros 422 trazem, para cada problema, **onde** ele ocorreu (`loc`), **o quê** (`msg`) e o **tipo** (`type`). A resposta **não repete o valor enviado**, para não devolver ao cliente texto hostil nem respostas enormes.

```json
{
  "detail": [
    {
      "loc": ["body", "severity"],
      "msg": "Input should be 'informational', 'low', 'medium', 'high' or 'critical'",
      "type": "enum"
    }
  ]
}
```

O exemplo é ilustrativo: o texto de `msg` vem do Pydantic e pode mudar entre versões.

## Limites

| Limite | Valor | Configurável |
|---|---|---|
| `source` | 1 a 100 caracteres | Não |
| `message` | 1 a 10.000 caracteres | Não |
| `hostname` | 1 a 255 caracteres | Não |
| `event_type` | 1 a 100 caracteres | Não |
| `username` | 1 a 256 caracteres | Não |
| `source_ip`, `destination_ip` | até 64 caracteres, endereço válido | Não |
| `timestamp` | entre 2000-01-01 e 2100-01-01 (UTC) | Não |
| Corpo de um pedido | 262.144 bytes (256 KiB) | Sim, por `VIGIL_MAX_BODY_BYTES` |
| Eventos por consulta (`limit`) | Padrão 50, máximo 200 | Não |
| `offset` e `event_id` | até 9.223.372.036.854.775.807 | Não |

## Códigos de resposta

| Código | Significado |
|---|---|
| 200 | Sucesso (`GET`) |
| 201 | Evento criado (`POST /events`) |
| 404 | Rota inexistente ou evento não encontrado |
| 405 | Método não permitido (por exemplo, `DELETE /events/1`) |
| 413 | Corpo do pedido grande demais |
| 422 | Dados inválidos |

## Não implementado

- Autenticação e autorização (planejado para a Fase 11).
- Filtros de pesquisa por data, IP, usuário ou gravidade (planejado para a Fase 10).
- Total de eventos na listagem e outros metadados de paginação.
- Envio de vários eventos em um único pedido.
- Detecção, correlação e alertas (Fases 6 a 8).
- Limitação de requisições por cliente.