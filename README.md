# Vigil SIEM

Um SIEM (Security Information and Event Management) construído do zero, com foco em aprendizado e portfólio de Blue Team / SOC.

> **Status: em desenvolvimento inicial.** Existe apenas uma API mínima com um endpoint de verificação de saúde e um teste automatizado. Nenhuma funcionalidade de SIEM (ingestão, detecção, alertas) está implementada ainda. Este README descreve o que existe hoje e o que está planejado, e é atualizado a cada etapa concluída.

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
| Testes | Pytest | Em uso (1 teste) |
| Banco de dados | SQLite no MVP (PostgreSQL depois), SQLAlchemy e Alembic | Planejado |
| Frontend | React, TypeScript, Vite, Tailwind CSS | Planejado |

## Funcionalidades

| Funcionalidade | Situação |
|---|---|
| Endpoint de saúde da API (`GET /health`) | Implementado |
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