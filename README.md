# Vigil SIEM

Um SIEM (Security Information and Event Management) construído do zero, com foco em aprendizado e portfólio de Blue Team / SOC.

> **Status: em desenvolvimento inicial.** Nenhuma funcionalidade está implementada ainda. Este README descreve o que existe hoje e o que está planejado, e será atualizado a cada etapa concluída.

## Objetivo

Construir uma aplicação real e funcional capaz de receber eventos de segurança, normalizá-los, detectar comportamentos suspeitos, gerar alertas e permitir investigação, com testes automatizados, documentação e histórico de commits organizado.

## Restrições do projeto

- **Custo zero:** apenas ferramentas gratuitas e open source, executadas localmente.
- **Windows e PowerShell:** o desenvolvimento acontece diretamente no Windows.
- **Sem Docker nas fases iniciais:** a containerização só entra em uma fase avançada, quando houver justificativa real.

## Stack planejada

| Camada | Tecnologia | Situação |
|---|---|---|
| Backend | Python, FastAPI, Pydantic | Planejado |
| Banco de dados | SQLite no MVP (PostgreSQL depois) com SQLAlchemy e Alembic | Planejado |
| Testes | Pytest | Planejado |
| Frontend | React, TypeScript, Vite, Tailwind CSS | Planejado |

## Módulos

| Módulo | Situação |
|---|---|
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

Ainda não há nada para executar. As instruções de instalação serão adicionadas quando o backend existir.

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).