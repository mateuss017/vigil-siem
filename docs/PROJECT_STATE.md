# Estado do Projeto

Este arquivo é a fonte de verdade sobre o andamento do desenvolvimento. Deve ser atualizado a cada etapa concluída e validada. Em caso de dúvida, o histórico do Git e os arquivos reais prevalecem sobre qualquer descrição.

## Posição atual

- **Fase atual:** 2 - Estrutura inicial
- **Etapa atual:** 2.5 - Registro de estado do projeto
- **Última etapa concluída:** 2.4 - README inicial
- **Último commit confirmado:** `32dcdbe docs: add initial README`
- **Próximo passo autorizado:** primeiro `git push` para o GitHub e criação do `ROADMAP.md`

## Funcionalidades

- **Implementadas:** nenhuma
- **Pendentes:** todas (ingestão, normalização, detecção, correlação, alertas, dashboard, investigação, autenticação)

## Arquivos importantes

- `.gitignore`: bloqueia segredos (`.env`), ambientes virtuais, bancos locais, logs e caches
- `LICENSE`: licença MIT
- `README.md`: apresentação do projeto, com a situação de cada módulo
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

- Windows com PowerShell 5.1
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