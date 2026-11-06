# Estado do Projeto

Este arquivo é a fonte de verdade sobre o andamento do desenvolvimento. Deve ser atualizado a cada etapa concluída e validada. Em caso de dúvida, o histórico do Git e os arquivos reais prevalecem sobre qualquer descrição.

## Posição atual

- **Fase atual:** 4 - API de ingestão (concluída, aguardando aprovação)
- **Etapa atual:** nenhuma em andamento
- **Última etapa concluída:** 4.6 - Documentação da Fase 4
- **Último commit confirmado:** `8bc5a20 docs: add API reference and security policy` (o commit que atualiza este arquivo vem logo depois e pode ser visto com `git log -1`)
- **Repositório remoto:** https://github.com/mateuss017/vigil-siem (público, branch `main`)
- **Próximo passo autorizado:** Fase 5 - Normalização e processamento (somente após aprovação)

## Funcionalidades

- **Implementadas:**
  - `GET /health`
  - `POST /events`: recebe, valida e grava um evento (campos `source` e `message`)
  - `GET /events`: lista eventos do mais novo para o mais antigo, com `limit` (padrão 50, máximo 200) e `offset`
  - Validação de entrada com schemas Pydantic
  - Limite de tamanho do corpo dos pedidos (256 KiB), com resposta 413
  - Configuração por variáveis de ambiente
  - Banco SQLite com SQLAlchemy e migração inicial com Alembic
- **Observações:**
  - A API **não tem autenticação** (Fase 11) e só deve escutar em `127.0.0.1`.
  - A aplicação não cria o banco ao iniciar: ele é criado com `python -m alembic upgrade head` (dentro de `backend/`).
  - O modelo `Event` é mínimo (`id`, `received_at`, `source`, `message`).
- **Pendentes:** normalização, detecção, correlação, alertas, dashboard, investigação, autenticação

## Arquivos importantes

- `.gitignore`: bloqueia segredos (`.env`), ambientes virtuais, bancos locais, logs e caches
- `LICENSE`: licença MIT
- `README.md`: apresentação, instruções de execução e situação de cada módulo
- `ROADMAP.md`: fases 0 a 14 e a situação de cada uma
- `CHANGELOG.md`: histórico de mudanças
- `SECURITY.md`: proteções existentes e limitações conhecidas
- `docs/API.md`: referência dos endpoints
- `.env.example`: modelo de configuração (o `.env` real não é versionado)
- `backend/app/main.py`: aplicação FastAPI, middleware de limite de tamanho e registro dos endpoints
- `backend/app/api/events.py`: endpoints `POST /events` e `GET /events`
- `backend/app/schemas/event.py`: schemas de entrada e saída dos eventos
- `backend/app/core/config.py`: configurações lidas de variáveis de ambiente
- `backend/app/core/limits.py`: middleware que limita o tamanho do corpo dos pedidos
- `backend/app/database/`: classe base dos modelos, engine, sessões, `get_db()` e `init_db()`
- `backend/app/models/event.py`: modelo mínimo de evento
- `backend/alembic.ini` e `backend/alembic/`: migrações do banco (`env.py` usa as configurações da aplicação)
- `backend/alembic/versions/574c08f80b4d_create_events_table.py`: migração inicial
- `backend/tests/`: testes (`conftest.py` reúne as preparações compartilhadas da API)
- `backend/requirements.txt`: dependências com versões exatas
- `docs/PROJECT_STATE.md`: este arquivo

## Decisões arquiteturais

- Monólito modular (sem microsserviços)
- Backend em Python com FastAPI, Pydantic e SQLAlchemy
- SQLite no MVP, com migração para PostgreSQL depois; endereço do banco configurável por `VIGIL_DATABASE_URL`
- Esquema do banco versionado com Alembic; o `env.py` reutiliza o engine da aplicação e usa `render_as_batch` por causa das limitações do SQLite
- `init_db()` (`create_all`) continua disponível e é usado pelos testes; o banco real deve ser criado pelas migrações
- Modelo `Event` propositalmente mínimo; os campos completos entram na Fase 5 (normalização)
- O `id` e o `received_at` são gerados pelo servidor; os schemas de entrada recusam esses campos e qualquer outro desconhecido
- O `commit` da gravação é feito pelo endpoint, e não pela dependência de sessão (`get_db`)
- Horário de recebimento gravado em UTC; o schema de saída trata horário sem fuso como UTC, pois o SQLite não guarda o fuso
- Eventos não podem ser alterados nem apagados pela API (sem rotas `PUT`, `PATCH` e `DELETE`)
- Listagem ordenada por horário e, no empate, por `id`, ambos do maior para o menor
- Limites: `source` até 100 caracteres, `message` até 10.000, corpo do pedido até 262.144 bytes (configurável) e listagem até 200 eventos por consulta
- Testes de banco, de migrações e da API usam SQLite em memória, sem tocar no banco real
- Frontend em React com TypeScript, a partir da Fase 9
- Licença MIT
- Sem Docker até a Fase 13
- Custo zero: apenas ferramentas gratuitas e locais
- Arquivos de texto gravados em UTF-8 sem BOM (o Windows PowerShell 5.1 grava com BOM por padrão)
- Cliente de testes da API: `httpx2`, porque o Starlette marcou o uso do `httpx` como obsoleto

## Ambiente

- Windows com PowerShell 5.1 (política de execução do usuário: RemoteSigned)
- Python 3.13.7, Git 2.56.0, VS Code 1.144.0
- Ambiente virtual `.venv` na raiz do projeto (não versionado)
- Banco local em `data/vigil.db` (não versionado), já marcado na migração inicial
- Node.js e npm: não instalados (necessários só na Fase 9)

## Dependências do projeto

Registradas em `backend/requirements.txt`: fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.2, pydantic-settings 2.16.2, SQLAlchemy 2.1.8, alembic 1.20.1, starlette 1.10.0, pytest 9.2.0, httpx2 2.16.0 e as dependências delas.

## Testes

- Testes automatizados: 83 (configuração, banco, migrações, schemas, sessão e API)
- Último resultado: 83 passed, sem avisos
- Verificação manual: ingestão e listagem testadas com o servidor real e um banco temporário, incluindo os códigos 422, 405 e 413

## Problemas conhecidos

- `httpx` e `httpcore` continuam em `requirements.txt` sem uso (o cliente de testes agora é o `httpx2`). Limpeza prevista para a Fase 12.
- Limitações de segurança listadas no `SECURITY.md` (sem autenticação, sem HTTPS, sem limitação de requisições por cliente, dados sem criptografia, dependências ainda não auditadas).

## Riscos pendentes

- Escopo grande para uma pessoa: manter o MVP pequeno e avançar uma etapa por vez
- SQLite tem limitações de concorrência: a troca de banco deve ser considerada ao longo do projeto
- Python 3.13 e bibliotecas recentes: conferir a compatibilidade de cada nova dependência antes de instalar
- A API aceita eventos sem autenticação: não expor a rede antes da Fase 11