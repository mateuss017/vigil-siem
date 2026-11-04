# Changelog

Todas as mudanças relevantes deste projeto são registradas neste arquivo.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado
- Estrutura inicial do repositório: `.gitignore`, licença MIT, README, ROADMAP e `docs/PROJECT_STATE.md`.
- API mínima com FastAPI e o endpoint `GET /health`.
- Primeiro teste automatizado com Pytest para o endpoint `/health`.
- Dependências do backend registradas em `backend/requirements.txt`.
- Configuração por variáveis de ambiente (prefixo `VIGIL_`) com `pydantic-settings` e o modelo `.env.example`.
- Camada de banco de dados com SQLAlchemy e SQLite local (`data/vigil.db`, fora do Git), tabela mínima `events` e testes que usam banco em memória.