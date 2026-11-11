# Política de segurança

O Vigil SIEM é um projeto em desenvolvimento, criado para aprendizado e portfólio. **Não use este software em produção nem exponha a API a uma rede.**

## Versões suportadas

O projeto ainda não tem versões publicadas. Apenas a branch `main` recebe correções.

## Como reportar uma vulnerabilidade

- Se a aba **Security** do repositório no GitHub oferecer a opção "Report a vulnerability", use-a. Assim o relato fica privado.
- Caso contrário, abra uma issue em https://github.com/mateuss017/vigil-siem/issues **sem detalhes que permitam explorar a falha** (por exemplo, descreva apenas que encontrou um problema de segurança), e o contato será combinado em seguida.

Não envie senhas, tokens ou dados pessoais reais em nenhum relato.

## O que está protegido hoje

Cada item abaixo é verificado por testes automatizados (pasta `backend/tests/`), e não apenas afirmado.

| Proteção | Como funciona | Testes |
|---|---|---|
| Validação da entrada | Campos obrigatórios, tamanhos mínimo e máximo, remoção de espaços, recusa de campos desconhecidos e de tipos errados | `test_schemas.py`, `test_event_create_fields.py`, `test_events_api.py`, `test_events_ingestion_api.py` |
| Injeção de SQL | O banco é acessado pelo SQLAlchemy, que envia os valores como dados e nunca os junta ao texto do comando SQL. Textos como `'; DROP TABLE events; --` são gravados como texto comum, em qualquer campo. | `test_events_security_api.py`, `test_events_ingestion_api.py` |
| Texto de XSS | Textos com `<script>` são guardados e devolvidos como texto, e as respostas são sempre JSON, e não HTML. A proteção no momento de **exibir** os eventos será tratada no frontend (Fase 9). | `test_events_security_api.py`, `test_events_ingestion_api.py` |
| Injeção em logs | Campos curtos (`source`, `hostname`, `event_type`, `username`) recusam quebras de linha e demais caracteres de controle. Na `message`, só são aceitos tabulação e quebras de linha. Byte nulo e `ESC` são recusados. | `test_input_hardening.py`, `test_event_create_fields.py` |
| Texto que não pode ser guardado | Caracteres Unicode inválidos (como um "surrogate" solto) são recusados com 422, em vez de causar um erro interno ao gravar. | `test_input_hardening.py` |
| Números fora do alcance do banco | `id` e `offset` acima do maior inteiro do SQLite recebem 422, e não um erro interno. | `test_events_detail_api.py`, `test_input_hardening.py` |
| Erros que não repetem a entrada | As respostas 422 trazem só onde, o quê e o tipo do erro. O texto enviado, mesmo hostil, não volta ao cliente, e nomes de campo com caracteres inválidos não quebram a resposta. | `test_validation_errors.py`, `test_errors_helpers.py` |
| Campos do servidor | Quem envia o evento não pode escolher o `id`, o `received_at` nem o `raw_event`. Isso impede forjar a hora em que um evento chegou ou o original guardado. | `test_events_api.py`, `test_events_ingestion_api.py` |
| Eventos imutáveis pela API | Não existe rota para alterar ou apagar eventos: `PUT`, `PATCH` e `DELETE` recebem 405, inclusive em `/events/{id}`. | `test_events_security_api.py`, `test_events_detail_api.py` |
| Limite de tamanho do pedido | Pedidos com mais de 256 KiB recebem 413 sem processar o conteúdo. O limite vale mesmo quando o cliente não declara o tamanho. | `test_events_limits_api.py` |
| Respostas de tamanho controlado | A listagem devolve no máximo 200 eventos e **não** inclui o `raw_event`. Um pedido enchido de espaços em branco só pesa na consulta de um evento isolado. | `test_events_list_api.py`, `test_events_detail_api.py` |
| Leitura tolerante | Uma linha do banco com valor inesperado na gravidade (por exemplo, editada à mão) não derruba a listagem. | `test_input_hardening.py` |
| Configuração fora do código | Endereço do banco e limites vêm de variáveis de ambiente. O arquivo `.env` real é bloqueado pelo `.gitignore`. | `test_config.py` |

## Limitações conhecidas

Estas limitações existem hoje e **não** estão resolvidas:

- **Sem autenticação nem autorização.** Qualquer programa que alcance a API pode gravar e ler eventos. Planejado para a Fase 11.
- **Sem HTTPS.** O tráfego é HTTP puro. Por isso o servidor deve escutar somente em `127.0.0.1`. **Nada no código impede** subir o servidor em outro endereço (por exemplo, com `--host 0.0.0.0`): essa escolha é feita no comando de execução. Não faça isso.
- **Sem limitação de requisições por cliente.** Um programa local pode enviar pedidos sem parar. Apenas o tamanho de cada pedido e a quantidade por consulta são limitados.
- **Os textos dos eventos são guardados como chegam.** Código HTML ou SQL dentro de `message`, `source`, `hostname`, `event_type` ou `username` é gravado como texto e devolvido como texto. Quem exibir esses dados (como o frontend futuro) precisa escapá-los.
- **Caracteres de controle do bloco C1** (de U+0080 a U+009F) não são recusados. Alguns terminais antigos os interpretam como comandos. Os controles ASCII (de U+0000 a U+001F e U+007F) são tratados como descrito acima.
- **O `raw_event` guarda o original sem filtro.** Ele pode conter qualquer texto que o JSON permita, incluindo códigos de escape escritos como `\u001b`.
- **Dados sem criptografia.** O banco SQLite (`data/vigil.db`) guarda o conteúdo dos eventos em texto comum. A proteção é a do próprio sistema operacional sobre o arquivo. A imutabilidade dos eventos vale só para a API: quem tiver acesso ao arquivo do banco pode alterá-lo.
- **Sem trilha de auditoria.** Não há registro de quem gravou ou leu eventos. Planejado junto com a autenticação.
- **Dependências ainda não auditadas.** Não foi feita varredura de vulnerabilidades nas bibliotecas. Prevista para a Fase 12.
- **Banco não criado automaticamente.** Se o banco não tiver sido criado com o Alembic, o comportamento da API não está coberto por testes.

## Boas práticas para quem executa o projeto

- Execute apenas em ambiente próprio ou autorizado.
- Nunca versione o arquivo `.env`, bancos de dados (`*.db`), cópias de segurança deles nem dados reais de eventos. A pasta `data/` é ignorada pelo Git.
- Faça uma cópia do banco antes de aplicar migrações.
- Não use dados pessoais ou sensíveis reais nos testes e nas demonstrações.