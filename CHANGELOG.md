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
- Migrações do banco com Alembic: migração inicial da tabela `events`, ambiente ligado às configurações da aplicação e testes que verificam subida, descida e sincronia com os modelos.
- Schemas de validação dos eventos (`EventCreate` e `EventRead`), que recusam campos ausentes, vazios, grandes demais, de tipo errado ou desconhecidos.
- Sessão de banco por requisição (`get_db`), fechada ao fim de cada pedido mesmo em caso de erro.
- Endpoint `POST /events`: recebe, valida e grava um evento. O `id` e o horário de recebimento são gerados pelo servidor.
- Endpoint `GET /events`: lista eventos do mais novo para o mais antigo, com `limit` (padrão 50, máximo 200) e `offset`.
- Limite de tamanho do corpo dos pedidos (padrão 256 KiB, configurável por `VIGIL_MAX_BODY_BYTES`), com resposta 413 mesmo quando o cliente não declara o tamanho.
- Testes de segurança da entrada: injeção de SQL, texto de XSS, caracteres especiais, tipos errados e ausência de rotas para alterar ou apagar eventos.
- Documentação da API (`docs/API.md`) e política de segurança (`SECURITY.md`), com as limitações conhecidas.

### Corrigido
- O horário de recebimento devolvido pela API agora sempre indica UTC. O SQLite não guarda o fuso, e o horário voltava sem essa informação.