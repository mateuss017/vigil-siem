# Changelog

Todas as mudanças relevantes deste projeto são registradas neste arquivo.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado
- Estrutura inicial do repositório: `.gitignore`, licença MIT, README, ROADMAP e `docs/PROJECT_STATE.md`.
- API com FastAPI: `GET /health`, `POST /events`, `GET /events` e `GET /events/{event_id}`.
- Configuração por variáveis de ambiente (prefixo `VIGIL_`) com `pydantic-settings` e o modelo `.env.example`.
- Banco SQLite com SQLAlchemy e migrações com Alembic: criação da tabela `events` e, depois, as colunas dos campos normalizados.
- Sessão de banco por requisição (`get_db`), fechada ao fim de cada pedido mesmo em caso de erro.
- Campos opcionais do evento: `timestamp`, `hostname`, `event_type`, `severity`, `source_ip`, `destination_ip` e `username`, validados e normalizados na entrada (horário em UTC, IPs na forma padrão, gravidade em cinco níveis, textos sem espaços nas pontas e sem caracteres de controle).
- Normalizador (`backend/app/processing/normalizer.py`) que monta o registro do banco e guarda o corpo original do pedido em `raw_event`, exatamente como chegou.
- Consulta de um evento isolado (`GET /events/{event_id}`), única rota que devolve o `raw_event`, com resposta 404 quando o evento não existe.
- Limite de tamanho do corpo dos pedidos (padrão 256 KiB, configurável por `VIGIL_MAX_BODY_BYTES`), com resposta 413 mesmo quando o cliente não declara o tamanho.
- Tratamento dos erros de validação (422) que informa onde, o quê e o tipo do erro, sem repetir o texto enviado.
- Testes automatizados (253): configuração, banco, migrações (incluindo a preservação de dados), schemas, normalizador, API, segurança da entrada e endurecimento contra entradas hostis.
- Documentação: `docs/API.md`, `docs/DATABASE.md` e `SECURITY.md`, com as limitações conhecidas.

### Alterado
- `POST /events` passou a aceitar os campos opcionais e a gravá-los normalizados. A resposta do `POST` e a listagem não incluem o `raw_event`.
- O campo `source` passou a recusar caracteres de controle. A `message` aceita quebras de linha e tabulações, mas recusa os demais caracteres de controle.
- Os erros 422 deixaram de repetir o valor enviado pelo cliente.
- A gravidade é lida do banco como texto comum, para que uma linha com valor inesperado não derrube a listagem.

### Corrigido
- O horário de recebimento devolvido pela API agora sempre indica UTC. O SQLite não guarda o fuso, e o horário voltava sem essa informação.
- Erro interno (500) com `offset` ou `id` maiores que o maior inteiro do SQLite: agora respondem 422.
- Erro interno (500) ao receber texto com Unicode inválido (um "surrogate" solto): agora responde 422.