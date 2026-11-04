# Estado do Projeto

Este arquivo é a fonte de verdade sobre o andamento do desenvolvimento. Deve ser atualizado a cada etapa concluída e validada. Em caso de dúvida, o histórico do Git e os arquivos reais prevalecem sobre qualquer descrição.

## Posição atual

- **Fase atual:** 2 - Estrutura inicial (concluída)
- **Etapa atual:** nenhuma em andamento; aguardando aprovação para iniciar a Fase 3
- **Última etapa concluída:** 2.8 - Fechamento da Fase 2
- **Último commit confirmado:** `2611f88 docs: add project roadmap` (o commit que atualiza este arquivo vem logo depois e pode ser visto com `git log -1`)
- **Repositório remoto:** https://github.com/mateuss017/vigil-siem (público, branch `main`)
- **Próximo passo autorizado:** Fase 3 - criar o ambiente virtual Python e iniciar o backend (somente após aprovação)

## Funcionalidades

- **Implementadas:** nenhuma
- **Pendentes:** todas (ingestão, normalização, detecção, correlação, alertas, dashboard, investigação, autenticação)

## Arquivos importantes

- `.gitignore`: bloqueia segredos (`.env`), ambientes virtuais, bancos locais, logs e caches
- `LICENSE`: licença MIT
- `README.md`: apresentação do projeto, com a situação de cada módulo
- `ROADMAP.md`: fases 0 a 14 e a situação de cada uma
- `docs/PROJECT_STATE.md`: este arquivo

## Decisões arquiteturais

- Monólito modular (sem microsserviços)
- Backend em Python com FastAPI, Pydantic e SQLAlchemy
- SQLite no MVP, com migração para PostgreSQL depois
- Frontend em React com TypeScript, a partir da Fase 9
- Licença MIT
- Sem Docker até a Fase 13
- Custo zero: apenas ferramentas gratuitas e locais
- Arquivos de texto gravados em UTF-8 sem BOM (o Windows PowerShell 5.1 grava com BOM por padrão)

## Ambiente

- Windows com PowerShell 5.1 (política de execução do usuário: RemoteSigned)
- Python 3.13.7, Git 2.56.0, VS Code 1.144.0
- Node.js e npm: não instalados (necessários só na Fase 9)

## Dependências do projeto

Nenhuma instalada. O ambiente virtual ainda não foi criado.

## Testes

Nenhum teste existe ainda.

## Problemas conhecidos

Nenhum.

## Riscos pendentes

- Escopo grande para uma pessoa: manter o MVP pequeno e avançar uma etapa por vez
- SQLite tem limitações de concorrência: a troca de banco deve ser considerada na Fase 3 e depois
- Python 3.13 é recente: antes de instalar dependências, conferir se as bibliotecas escolhidas o suportam