# Roadmap

Legenda: **Concluída** | **Em andamento** | **Planejada**

O estado detalhado do desenvolvimento fica em [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md). Cada fase só é marcada como concluída depois de implementada, testada, documentada e versionada.

| Fase | Nome | Objetivo | Situação |
|---|---|---|---|
| 0 | Planejamento e análise | Definir escopo, stack, arquitetura e riscos | Concluída |
| 1 | Preparação do ambiente | Verificar Python, Git, VS Code e PowerShell | Concluída |
| 2 | Estrutura inicial | Repositório, .gitignore, licença, README, estado do projeto | Concluída |
| 3 | Backend e persistência | FastAPI, banco SQLite, models, schemas, migrações e primeiros testes | Planejada |
| 4 | API de ingestão | Endpoint JSON com validação e persistência de eventos | Planejada |
| 5 | Normalização e processamento | Modelo de evento padronizado (inspirado no ECS) | Planejada |
| 6 | Motor de detecção | Regras configuráveis, severidade e histórico de detecções | Planejada |
| 7 | Correlação | Agrupamento por IP, usuário, host e janela de tempo | Planejada |
| 8 | Alertas | Geração, estados (aberto, em investigação, resolvido, falso positivo) e histórico | Planejada |
| 9 | Frontend | React com TypeScript e dashboard com dados reais | Planejada |
| 10 | Investigação | Pesquisa, filtros, detalhes e linha do tempo | Planejada |
| 11 | Autenticação | Login, perfis, proteção de endpoints e auditoria | Planejada |
| 12 | Testes e segurança | Cobertura, revisão de segurança e correções | Planejada |
| 13 | Docker e infraestrutura | Containerização, só depois de o sistema estar estável | Planejada |
| 14 | Finalização e publicação | Documentação final, screenshots reais, CI e release | Planejada |

## Observações

- O MVP corresponde às fases 3 a 8: backend funcional que recebe eventos, detecta comportamentos suspeitos e gera alertas.
- A posição da autenticação (fase 11) será reavaliada ao final da fase 8, pois pode fazer sentido antecipá-la antes do frontend.
- Fora do MVP: Syslog, Windows Event Logs, MITRE ATT&CK, Threat Intelligence, OpenSearch.