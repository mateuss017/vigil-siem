# Estado do Projeto

Este arquivo é a fonte de verdade sobre o andamento do desenvolvimento. Deve ser atualizado a cada etapa concluída e validada. Em caso de dúvida, o histórico do Git e os arquivos reais prevalecem sobre qualquer descrição.

## Posição atual

- **Fase atual:** 3 - Backend e persistência (em andamento)
- **Etapa atual:** 3.7 - Banco SQLite com SQLAlchemy (concluída, aguardando push)
- **Última etapa concluída:** 3.7 - Banco SQLite com SQLAlchemy
- **Último commit confirmado:** `15cdce1 chore(backend): add sqlalchemy` (o commit desta etapa vem logo depois e pode ser visto com `git log -1`)
- **Repositório remoto:** https://github.com/mateuss017/vigil-siem (público, branch `main`)
- **Próximo passo autorizado:** etapa 3.8, migrações com Alembic (somente após aprovação)

## Funcionalidades

- **Implementadas:** endpoint `GET /health`; configuração por variáveis de ambiente; conexão com SQLite via SQLAlchemy; tabela mínima `events` (id, received_at, source, message)
- **Observação:** a aplicação ainda não cria o banco ao iniciar e não há API para gravar eventos. O banco só é exercitado pelos testes e por chamada manual de `init_db()`.
- **Pendentes:** ingestão, normalização, detecção, correlação, alertas, dashboard, investigação, autenticação, migrações, schemas

## Arquivos importantes

- `.gitignore`: bloqueia segredos (`.env`), ambientes virtuais, bancos locais, logs e caches
- `LICENSE`: licença MIT
- `README.md`: apresentação do projeto, instruções de execução e situação de cada módulo
- `ROADMAP.md`: fases 0 a 14 e a situação de cada uma
- `CHANGELOG.md`: histórico de mudanças
- `.env.example`: modelo de configuração (o `.env` real não é versionado)
- `backend/app/main.py`: aplicação FastAPI com o endpoint `/health`
- `backend/app/core/config.py`: configurações lidas de variáveis de ambiente
- `backend/app/database/base.py`: classe base dos modelos
- `backend/app/database/session.py`: engine, sessões e `init_db()`
- `backend/app/models/event.py`: modelo mínimo de evento
- `backend/tests/`: testes de health, configuração e banco de dados
- `backend/pytest.ini`: configuração do Pytest
- `backend/requirements.txt`: dependências com versões exatas
- `docs/PROJECT_STATE.md`: este arquivo

## Decisões arquiteturais

- Monólito modular (sem microsserviços)
- Backend em Python com FastAPI, Pydantic e SQLAlchemy
- SQLite no MVP, com migração para PostgreSQL depois; endereço do banco configurável por `VIGIL_DATABASE_URL`
- Tabelas criadas por `init_db()` (`create_all`) por enquanto; migrações com Alembic na próxima etapa
- Modelo `Event` propositalmente mínimo; os campos completos entram na Fase 5 (normalização)
- Testes de banco usam SQLite em memória, sem tocar no banco real
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
- Banco local em `data/vigil.db` (não versionado)
- Node.js e npm: não instalados (necessários só na Fase 9)

## Dependências do projeto

Registradas em `backend/requirements.txt`: fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.2, pydantic-settings 2.16.2, SQLAlchemy 2.1.8, starlette 1.10.0, pytest 9.2.0, httpx2 2.16.0 e as dependências delas.

## Testes

- Testes automatizados: 6 (`test_health.py`, `test_config.py`, `test_database.py`)
- Último resultado: 6 passed, sem avisos

## Problemas conhecidos

- `httpx` e `httpcore` continuam em `requirements.txt` sem uso (o cliente de testes agora é o `httpx2`). Limpeza prevista para a Fase 12.

## Riscos pendentes

- Escopo grande para uma pessoa: manter o MVP pequeno e avançar uma etapa por vez
- SQLite tem limitações de concorrência: a troca de banco deve ser considerada ao longo do projeto
- Python 3.13 e bibliotecas recentes: conferir a compatibilidade de cada nova dependência antes de instalar