# API do Vigil SIEM

Referência dos endpoints da API. Este documento descreve apenas o que está **implementado e verificado** (por testes automatizados e por uma demonstração manual com o servidor real). O que ainda não existe está na seção [Não implementado](#não-implementado).

> **Aviso:** a API **não tem autenticação**. Qualquer programa que consiga acessar o servidor pode gravar e ler eventos. Use somente em ambiente local, com o servidor escutando em `127.0.0.1`. Veja o [SECURITY.md](../SECURITY.md).

## Visão geral

| Endpoint | Função | Situação |
|---|---|---|
| `GET /health` | Informa que a aplicação está no ar | Implementado |
| `POST /events` | Recebe e grava um evento | Implementado |
| `GET /events` | Lista os eventos gravados | Implementado |
| `GET /events/{id}` | Consulta um evento isolado | Não implementado |
| Alteração e remoção de eventos | `PUT`, `PATCH`, `DELETE` | Não implementado, de propósito |

## Como acessar

Com o servidor no ar (veja o [README](../README.md)), a API responde em `http://127.0.0.1:8000`. A documentação interativa gerada automaticamente pelo FastAPI fica em `http://127.0.0.1:8000/docs`.

O banco de dados precisa ter sido criado antes com `python -m alembic upgrade head` (dentro de `backend/`). A aplicação **não** cria o banco ao iniciar.

## Convenções

- Corpo dos pedidos e das respostas em **JSON**, com codificação **UTF-8**.
- Horários em **UTC**, no formato ISO 8601.
- O `id` e o horário de recebimento (`received_at`) são gerados pelo **servidor**. Quem envia o evento não pode escolhê-los.
- Eventos **não podem ser alterados nem apagados** pela API.

## GET /health

Confere se a aplicação está no ar.

**Resposta (200):**

```json
{"status": "ok"}
```

## POST /events

Recebe um evento, valida, grava no banco e devolve o evento criado.

### Corpo do pedido

| Campo | Tipo | Regras |
|---|---|---|
| `source` | texto | Obrigatório. De 1 a 100 caracteres, depois de remover os espaços das pontas. Identifica a origem do evento. |
| `message` | texto | Obrigatório. De 1 a 10.000 caracteres, depois de remover os espaços das pontas. |

Outras regras:

- Campos **desconhecidos** são recusados (incluindo `id` e `received_at`).
- Textos vazios ou só com espaços são recusados.
- Valores de tipo errado (número, lista, objeto, `null`) são recusados.
- O corpo inteiro do pedido não pode passar de **262.144 bytes** (256 KiB). O limite pode ser alterado pela variável `VIGIL_MAX_BODY_BYTES`.

### Resposta (201)

```json
{
  "id": 1,
  "received_at": "2026-11-06T14:30:00Z",
  "source": "firewall-01",
  "message": "login falhou para o usuario admin"
}
```

Os valores acima são ilustrativos. O `received_at` é o horário em que o servidor recebeu o evento, em UTC.

### Exemplo (PowerShell)

```powershell
$evento = @{ source = "firewall-01"; message = "login falhou para o usuario admin" } | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($evento)
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/events -ContentType "application/json" -Body $bytes
```

O texto é convertido em bytes UTF-8 antes do envio porque o Windows PowerShell 5.1 pode corromper acentos ao enviar texto direto.

### Erros

| Código | Quando acontece |
|---|---|
| 413 | O corpo do pedido passa de 262.144 bytes. A resposta é `{"detail": "Request body too large."}` e nada é gravado. |
| 422 | O corpo não é um JSON válido ou não respeita as regras de validação. O FastAPI devolve um JSON com o campo `detail` descrevendo o problema. Nada é gravado. |

## GET /events

Lista os eventos gravados, do **mais novo para o mais antigo**. Eventos recebidos no mesmo instante são ordenados pelo `id`, do maior para o menor, para que a ordem seja sempre a mesma.

### Parâmetros de consulta

| Parâmetro | Tipo | Padrão | Regras |
|---|---|---|---|
| `limit` | inteiro | 50 | De 1 a 200. Quantidade máxima de eventos devolvidos. |
| `offset` | inteiro | 0 | Zero ou maior. Quantidade de eventos a pular, para ler a lista em páginas. |

### Resposta (200)

Uma lista de eventos, cada um com `id`, `received_at`, `source` e `message`. Se não houver eventos, a lista vem vazia (`[]`).

### Exemplos (PowerShell)

```powershell
# Os 50 eventos mais recentes (padrão)
Invoke-RestMethod http://127.0.0.1:8000/events

# Segunda página, com 2 eventos por página
Invoke-RestMethod "http://127.0.0.1:8000/events?limit=2&offset=2"
```

### Erros

| Código | Quando acontece |
|---|---|
| 422 | `limit` fora do intervalo de 1 a 200, `offset` negativo ou valores que não são números. |

## Limites

| Limite | Valor | Configurável |
|---|---|---|
| Tamanho de `source` | 1 a 100 caracteres | Não |
| Tamanho de `message` | 1 a 10.000 caracteres | Não |
| Tamanho do corpo de um pedido | 262.144 bytes (256 KiB) | Sim, por `VIGIL_MAX_BODY_BYTES` |
| Eventos por consulta (`limit`) | Padrão 50, máximo 200 | Não |

## Códigos de resposta

| Código | Significado |
|---|---|
| 200 | Sucesso (`GET`) |
| 201 | Evento criado (`POST /events`) |
| 404 | Rota inexistente (por exemplo, `GET /events/1`) |
| 405 | Método não permitido (por exemplo, `DELETE /events`) |
| 413 | Corpo do pedido grande demais |
| 422 | Dados inválidos |

## Não implementado

- Autenticação e autorização (planejado para a Fase 11).
- Consulta de um evento isolado (`GET /events/{id}`).
- Filtros de pesquisa por data, IP, usuário ou severidade (planejado para a Fase 10).
- Campos normalizados do evento, como `hostname`, IPs, usuário e severidade (planejado para a Fase 5).
- Limitação de requisições por cliente.