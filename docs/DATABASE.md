# Banco de dados

Descrição do banco de dados do Vigil SIEM: o que é guardado, como o esquema evolui e como operá-lo. Este documento descreve apenas o que existe e foi verificado.

## Visão geral

- **Banco:** SQLite, em um arquivo local. Por padrão, `data/vigil.db` na raiz do projeto (pasta ignorada pelo Git). O caminho pode ser trocado com a variável `VIGIL_DATABASE_URL`.
- **Acesso:** SQLAlchemy 2, sempre com valores enviados como dados (nunca juntados ao texto do comando SQL).
- **Esquema:** versionado com o Alembic, na pasta `backend/alembic/`.
- **Criação:** a aplicação **não** cria o banco ao iniciar. Ele é criado com `python -m alembic upgrade head`, dentro de `backend/`.
- **Troca futura:** o plano é migrar para PostgreSQL quando houver necessidade. O código foi escrito com SQLAlchemy para facilitar essa troca.

## Tabela `events`

| Coluna | Tipo | Aceita vazio | Significado |
|---|---|---|---|
| `id` | inteiro, chave primária | Não | Número do evento, gerado pelo banco |
| `received_at` | data e hora | Não | Quando o evento **chegou** ao SIEM. UTC, gerado pelo servidor |
| `source` | texto, até 100 | Não | Origem do evento |
| `message` | texto longo | Não | Descrição do evento |
| `timestamp` | data e hora | Sim | Quando o evento **aconteceu** na origem. UTC |
| `hostname` | texto, até 255 | Sim | Máquina de origem, em minúsculas |
| `event_type` | texto, até 100 | Sim | Tipo do evento, em minúsculas |
| `severity` | texto, até 20 | Sim | `informational`, `low`, `medium`, `high` ou `critical` |
| `source_ip` | texto, até 64 | Sim | IP de origem, na forma padrão |
| `destination_ip` | texto, até 64 | Sim | IP de destino, na forma padrão |
| `username` | texto, até 256 | Sim | Usuário envolvido, com maiúsculas e minúsculas preservadas |
| `raw_event` | texto longo | Sim | O corpo do pedido original, exatamente como chegou |

Pontos importantes:

- **Eventos antigos:** os eventos gravados antes dos campos novos existirem ficam com as colunas novas vazias. A migração não inventa valores.
- **Tamanhos:** o SQLite **não impõe** o tamanho declarado das colunas de texto. Quem impõe os limites é a API. Um teste (`test_model_schema_consistency.py`) garante que o tamanho de cada coluna é igual ao limite aceito pela API, para que a troca futura para um banco que impõe tamanhos (como o PostgreSQL) não recuse dados que a API aceitou.
- **Gravidade:** o banco não tem uma restrição que limite a gravidade aos cinco níveis. Quem garante isso é a API na entrada.
- **Fuso horário:** o SQLite não guarda o fuso. Os horários são sempre gravados em UTC, e a API restaura a indicação de UTC ao devolvê-los.
- **Índices:** só existe o da chave primária. A listagem ordena por `received_at`, o que em tabelas grandes exige varrer todas as linhas. Índices para essa ordenação e para os filtros de pesquisa serão criados nas fases em que essas consultas existirem (correlação e investigação), com base em medição.

## Tabelas `detections` e `detection_events`

Guardam o que as regras de detecção encontram e os eventos que servem de prova. As tabelas já existem no banco, mas **nenhuma regra grava nelas ainda**: o motor de detecção é da Fase 6, em andamento.

### `detections`

| Coluna | Tipo | Aceita vazio | Significado |
|---|---|---|---|
| `id` | inteiro, chave primária | Não | Número da detecção |
| `rule_id` | texto, até 100 | Não | Identificador estável da regra (por exemplo, `failed_login_burst`) |
| `severity` | texto, até 20 | Não | Gravidade da detecção |
| `group_key` | texto, até 255 | Sim | O que a regra agrupou (por exemplo, o IP de origem). Vazio nas regras que olham um evento isolado |
| `summary` | texto longo | Não | Descrição legível, escrita no momento da detecção |
| `window_start` | data e hora | Sim | Início da janela de tempo analisada (UTC). Vazio nas regras sem janela |
| `window_end` | data e hora | Sim | Fim da janela de tempo analisada (UTC) |
| `event_count` | inteiro | Não | Quantidade de eventos que a regra considerou |
| `created_at` | data e hora | Não | Quando a detecção foi gravada (UTC) |

### `detection_events`

Liga cada detecção aos eventos que a provam. Um evento pode provar várias detecções, e uma detecção tem vários eventos.

| Coluna | Tipo | Significado |
|---|---|---|
| `detection_id` | inteiro, chave estrangeira para `detections.id` | A detecção |
| `event_id` | inteiro, chave estrangeira para `events.id` | O evento que serve de prova |

A chave primária é o par (`detection_id`, `event_id`): o mesmo evento não pode ser ligado duas vezes à mesma detecção.

Regras de integridade, verificadas por testes:

- uma prova só pode apontar para um evento que existe;
- apagar uma detecção apaga as ligações dela (`CASCADE`), mas **nunca** os eventos;
- um evento que serve de prova **não pode ser apagado** (`RESTRICT`).

Essas regras dependem da verificação de chaves estrangeiras do SQLite, que vem **desligada** por padrão e vale só para a conexão em que é ligada. A aplicação a liga a cada conexão (`PRAGMA foreign_keys=ON`, em `database/session.py`). Quem abrir o arquivo do banco em outra ferramenta precisa ligá-la por conta própria.

## Migrações

| Revisão | Arquivo | O que faz |
|---|---|---|
| `574c08f80b4d` | `574c08f80b4d_create_events_table.py` | Cria a tabela `events` com `id`, `received_at`, `source` e `message` |
| `6c8445d95a33` | `6c8445d95a33_add_normalized_event_fields.py` | Acrescenta as 8 colunas opcionais (`timestamp`, `hostname`, `event_type`, `severity`, `source_ip`, `destination_ip`, `username`, `raw_event`) |
| `f6f62d67b008` | `f6f62d67b008_add_detections_tables.py` | Cria as tabelas `detections` e `detection_events` |

Cada migração tem uma função `upgrade()` (avançar) e uma `downgrade()` (voltar). Os testes (`test_migrations.py`) provam que:

- as migrações sobem e descem em um banco vazio;
- o banco migrado fica idêntico ao que o modelo descreve;
- um evento gravado antes da migração dos campos novos sobrevive intacto, com os campos novos vazios;
- desfazer a migração dos campos novos preserva as colunas originais e os seus dados.

### Comandos

Todos dentro da pasta `backend`, com o ambiente virtual ativo:

```powershell
# Criar o banco ou atualizá-lo até a migração mais recente
python -m alembic upgrade head

# Ver em que migração o banco está
python -m alembic current

# Conferir se o modelo e as migrações estão em sincronia
python -m alembic check

# Gerar uma nova migração a partir de uma mudança no modelo (revisar o arquivo gerado antes de usar)
python -m alembic revision --autogenerate -m "descricao da mudanca"
```

### Boas práticas

- **Copie o banco antes de migrar:** `Copy-Item data\vigil.db data\vigil.db.bak` (a pasta `data/` é ignorada pelo Git).
- **Revise toda migração gerada automaticamente** antes de aplicá-la. O gerador pode errar, principalmente com tipos de coluna.
- **Cuidado com `downgrade`:** desfazer a migração `6c8445d95a33` **apaga** as 8 colunas novas e os dados que elas contêm. Os dados das colunas originais são preservados.
- **Cuidado com `downgrade`:** desfazer a migração `f6f62d67b008` **apaga** as tabelas de detecções e tudo que elas contêm; os eventos não são afetados.
- **Migrações que recriam a tabela `events`:** o modo "batch" recria a tabela para alguns tipos de mudança no SQLite, e a regra `RESTRICT` das provas pode impedir isso. Nesse caso, a migração precisa desligar a verificação de chaves estrangeiras durante a recriação. Adicionar colunas, como nas migrações atuais, não é afetado.
- **Teste em um banco temporário:** aponte `VIGIL_DATABASE_URL` para um arquivo novo, aplique e confira, e só depois migre o banco real.
- O modo "batch" do Alembic (`render_as_batch`) está ligado porque o SQLite tem limitações para alterar tabelas já existentes.

## Testes e o banco

Os testes automatizados usam um SQLite **temporário, em memória** (preparação `session_factory`, em `backend/tests/conftest.py`) e nunca tocam no banco real.