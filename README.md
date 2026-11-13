# Vigil SIEM

Um SIEM (Security Information and Event Management) construído do zero, com foco em aprendizado e portfólio de Blue Team / SOC.

> **Status: em desenvolvimento.** Já existe uma API que recebe, normaliza e guarda eventos de segurança, com banco SQLite versionado por migrações e testes automatizados. Detecção, correlação, alertas, dashboard e autenticação **ainda não estão implementados**, e a API **não tem autenticação**: use apenas em ambiente local. Este README descreve o que existe hoje e o que está planejado, e é atualizado a cada etapa concluída.

## Objetivo

Construir uma aplicação real e funcional capaz de receber eventos de segurança, normalizá-los, detectar comportamentos suspeitos, gerar alertas e permitir investigação, com testes automatizados, documentação e histórico de commits organizado.

## Restrições do projeto

- **Custo zero:** apenas ferramentas gratuitas e open source, executadas localmente.
- **Windows e PowerShell:** o desenvolvimento acontece diretamente no Windows.
- **Sem Docker nas fases iniciais:** a containerização só entra em uma fase avançada, quando houver justificativa real.

## Stack

| Camada | Tecnologia | Situação |
|---|---|---|
| Backend | Python, FastAPI, Pydantic | Em uso |
| Banco de dados | SQLite no MVP (PostgreSQL depois) com SQLAlchemy | Em uso |
| Migrações do banco | Alembic | Em uso (2 migrações) |
| Testes | Pytest | Em uso (253 testes) |
| Frontend | React, TypeScript, Vite, Tailwind CSS | Planejado |

## Funcionalidades

| Funcionalidade | Situação |
|---|---|
| Endpoint de saúde da API (`GET /health`) | Implementado |
| Ingestão de eventos por API (`POST /events`), com validação e limite de tamanho | Implementado |
| Normalização dos eventos (horário em UTC, IPs em forma padrão, gravidade em 5 níveis, textos higienizados) com preservação do original (`raw_event`) | Implementado |
| Listagem de eventos (`GET /events`), com limite e paginação | Implementado |
| Consulta de um evento isolado, com o original recebido (`GET /events/{id}`) | Implementado |
| Persistência em SQLite, com migrações | Implementado |
| Motor de detecção | Planejado |
| Correlação de eventos | Planejado |
| Alertas e seus estados | Planejado |
| Dashboard | Planejado |
| Investigação (filtros e pesquisa) | Planejado |
| Autenticação e auditoria | Planejado |
| Integrações (Syslog, Windows Event Logs, MITRE ATT&CK) | Planejado, fora do MVP |

## Como executar

Pré-requisitos: Windows, PowerShell, Python 3.11 ou superior e Git. Testado com Python 3.13.

**1. Obter o código e instalar as dependências:**

```powershell
git clone https://github.com/mateuss017/vigil-siem.git
cd vigil-siem
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

**2. Criar o banco de dados** (a aplicação não o cria sozinha ao iniciar):

```powershell
cd backend
python -m alembic upgrade head
```

**3. Subir a API**, escutando apenas no seu computador:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Com o servidor no ar, `http://127.0.0.1:8000/docs` mostra a documentação interativa gerada automaticamente. Para parar o servidor, use `Ctrl+C`.

**4. Enviar e listar um evento** (em outro terminal):

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
$eventos = Invoke-RestMethod http://127.0.0.1:8000/events
$eventos
```

O evento volta normalizado (`hostname` em minúsculas, `severity` como `high`). Todos os endpoints, campos, limites e códigos de resposta estão em [docs/API.md](docs/API.md).

> **Segurança:** a API não tem autenticação nem HTTPS. Nunca suba o servidor em outro endereço que não `127.0.0.1`. Veja o [SECURITY.md](SECURITY.md).

## Configuração

Copie o modelo e ajuste os valores se quiser (o arquivo `.env` não é versionado):

```powershell
Copy-Item .env.example .env
```

Sem um `.env`, a aplicação usa valores padrão seguros, inclusive um banco SQLite local em `data/vigil.db` (pasta ignorada pelo Git). O caminho pode ser trocado com `VIGIL_DATABASE_URL`, e o tamanho máximo do corpo de um pedido com `VIGIL_MAX_BODY_BYTES`.

## Banco de dados e migrações

O esquema do banco é versionado com o Alembic. Para criar o banco ou atualizá-lo até a migração mais recente (dentro da pasta `backend`, com o ambiente virtual ativo):

```powershell
python -m alembic upgrade head
```

Para conferir se os modelos e as migrações estão em sincronia:

```powershell
python -m alembic check
```

Faça uma cópia do banco antes de migrar. A tabela, as migrações e os cuidados estão em [docs/DATABASE.md](docs/DATABASE.md).

## Testes

Com o ambiente virtual ativo:

```powershell
cd backend
python -m pytest -v
```

Os testes usam um banco SQLite temporário em memória e nunca tocam no banco real.

## Documentação

- [docs/API.md](docs/API.md): referência da API
- [docs/DATABASE.md](docs/DATABASE.md): tabela, migrações e operação do banco
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): organização do código e fluxo de um evento
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): como desenvolver, testar e versionar
- [SECURITY.md](SECURITY.md): proteções existentes e limitações conhecidas
- [ROADMAP.md](ROADMAP.md): fases do projeto e situação de cada uma
- [CHANGELOG.md](CHANGELOG.md): histórico de mudanças
- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md): estado detalhado do desenvolvimento

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).