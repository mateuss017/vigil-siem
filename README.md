# Vigil SIEM

Um SIEM (Security Information and Event Management) construído do zero, com foco em aprendizado e portfólio de Blue Team / SOC.

> **Status: em desenvolvimento inicial.** Existem uma API mínima com endpoint de verificação de saúde, configuração por variáveis de ambiente e uma tabela mínima de eventos em SQLite com migrações, tudo com testes automatizados. Nenhuma funcionalidade de SIEM (ingestão, detecção, alertas) está implementada ainda. Este README descreve o que existe hoje e o que está planejado, e é atualizado a cada etapa concluída.

## Objetivo

Construir uma aplicação real e funcional capaz de receber eventos de segurança, normalizá-los, detectar comportamentos suspeitos, gerar alertas e permitir investigação, com testes automatizados, documentação e histórico de commits organizado.

## Restrições do projeto

- **Custo zero:** apenas ferramentas gratuitas e open source, executadas localmente.
- **Windows e PowerShell:** o desenvolvimento acontece diretamente no Windows.
- **Sem Docker nas fases iniciais:** a containerização só entra em uma fase avançada, quando houver justificativa real.

## Stack

| Camada | Tecnologia | Situação |
|---|---|---|
| Backend | Python, FastAPI, Pydantic | Em uso (API mínima) |
| Testes | Pytest | Em uso (9 testes) |
| Banco de dados | SQLite no MVP (PostgreSQL depois) com SQLAlchemy | Em uso (tabela mínima de eventos) |
| Migrações do banco | Alembic | Em uso (migração inicial da tabela de eventos) |
| Frontend | React, TypeScript, Vite, Tailwind CSS | Planejado |

## Funcionalidades

| Funcionalidade | Situação |
|---|---|
| Endpoint de saúde da API (`GET /health`) | Implementado |
| Persistência: tabela mínima de eventos em SQLite (ainda sem API para gravar eventos) | Implementado |
| Ingestão de eventos por API | Planejado |
| Normalização de eventos | Planejado |
| Motor de detecção | Planejado |
| Correlação de eventos | Planejado |
| Alertas e seus estados | Planejado |
| Dashboard | Planejado |
| Investigação | Planejado |
| Autenticação e auditoria | Planejado |
| Integrações (Syslog, Windows Event Logs, MITRE ATT&CK) | Planejado, fora do MVP |

## Como executar

Pré-requisitos: Windows, PowerShell, Python 3.11 ou superior e Git. Testado com Python 3.13.

```powershell
git clone https://github.com/mateuss017/vigil-siem.git
cd vigil-siem
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Subir a API (o servidor escuta apenas em `127.0.0.1`):

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Com o servidor no ar, `http://127.0.0.1:8000/health` responde `{"status":"ok"}` e `http://127.0.0.1:8000/docs` mostra a documentação interativa gerada automaticamente.

## Configuração

Copie o modelo e ajuste os valores se quiser (o arquivo `.env` não é versionado):

```powershell
Copy-Item .env.example .env
```

Sem um `.env`, a aplicação usa valores padrão seguros, inclusive um banco SQLite local em `data/vigil.db` (pasta ignorada pelo Git). O caminho pode ser trocado com `VIGIL_DATABASE_URL`.

## Banco de dados e migrações

O esquema do banco é versionado com o Alembic. Para criar o banco (ou atualizá-lo até a migração mais recente), com o ambiente virtual ativo:

```powershell
cd backend
python -m alembic upgrade head
```

Para conferir se os modelos e as migrações estão em sincronia:

```powershell
python -m alembic check
```

A aplicação ainda não cria o banco sozinha ao iniciar: use o comando acima.

## Testes

Com o ambiente virtual ativo:

```powershell
cd backend
python -m pytest -v
```

## Documentação

- [ROADMAP.md](ROADMAP.md): fases do projeto e situação de cada uma
- [CHANGELOG.md](CHANGELOG.md): histórico de mudanças
- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md): estado detalhado do desenvolvimento

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).