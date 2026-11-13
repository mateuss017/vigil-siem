# Guia de desenvolvimento

Como configurar o ambiente, rodar, testar, migrar e versionar o Vigil SIEM. Os comandos são para o **Windows PowerShell**, a partir da raiz do projeto, salvo indicação em contrário.

## Ambiente

Versões com as quais o projeto foi desenvolvido e testado:

| Ferramenta | Versão |
|---|---|
| Windows PowerShell | 5.1 |
| Python | 3.13.7 (o projeto exige 3.11 ou superior) |
| Git | 2.56.0 |
| VS Code | 1.144.0 |

O Node.js só será necessário na Fase 9 (frontend).

## Configuração inicial

```powershell
git clone https://github.com/mateuss017/vigil-siem.git
cd vigil-siem
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd backend
python -m alembic upgrade head
cd ..
```

O ambiente virtual precisa ser ativado a cada terminal novo. Com ele ativo, o prompt começa com `(.venv)`. Se o PowerShell recusar executar o script de ativação, confira a política de execução do usuário (`Get-ExecutionPolicy -List`): `RemoteSigned` no escopo `CurrentUser` é suficiente.

## Dia a dia

### Rodar os testes

Os testes devem ser executados de dentro da pasta `backend`, onde fica o `pytest.ini`:

```powershell
cd backend
python -m pytest -q                      # todos os testes, saída curta
python -m pytest -v                      # todos, com o nome de cada teste
python -m pytest tests\test_normalizer.py   # um arquivo
python -m pytest -k "severity"           # só testes cujo nome contém a palavra
python -m pytest -x --tb=short           # para no primeiro erro, com traceback curto
cd ..
```

Os testes usam um SQLite temporário em memória e nunca tocam no banco real.

### Subir a API

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use sempre `--host 127.0.0.1`: a API não tem autenticação nem HTTPS. A documentação interativa fica em `http://127.0.0.1:8000/docs`.

### Testar com um banco temporário

Para experimentar sem tocar no `data/vigil.db`, aponte a configuração para outro arquivo (só vale na janela atual do terminal):

```powershell
$db = (Join-Path (Get-Location) "data\teste.db").Replace("\", "/")
$env:VIGIL_DATABASE_URL = "sqlite:///$db"
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ao terminar, pare o servidor, limpe a variável e apague o arquivo:

```powershell
Remove-Item Env:VIGIL_DATABASE_URL
Remove-Item data\teste.db
```

## Migrações do banco

Fluxo para mudar o esquema (os comandos estão em [DATABASE.md](DATABASE.md)):

1. Altere o modelo em `backend/app/models/`.
2. Gere a migração em um banco temporário (como acima), com `python -m alembic revision --autogenerate -m "descricao"`.
3. **Leia o arquivo gerado.** O gerador pode errar, principalmente com tipos de coluna.
4. Aplique e desfaça a migração no banco temporário (`upgrade head` e `downgrade -1`).
5. Escreva um teste que prove que os dados existentes sobrevivem (veja `test_migrations.py`).
6. Faça uma cópia do `data/vigil.db` e só então aplique a migração nele.

O teste `test_migrations_match_models` falha se o modelo e as migrações ficarem fora de sincronia.

## Como adicionar uma funcionalidade

1. Defina o formato dos dados em `schemas/` e escreva os testes dele.
2. Se houver tabela nova ou coluna nova, ajuste o modelo e crie a migração (seção anterior).
3. Escreva a regra de negócio na pasta correspondente.
4. Exponha em `api/` e escreva os testes de integração. Use a preparação `client` (ou `lenient_client`, que devolve erros internos como resposta 500) do `backend/tests/conftest.py`.
5. Teste entradas hostis: valores no limite, um acima do limite, tipos errados, texto com caracteres de controle, números enormes.
6. Atualize a documentação: `docs/API.md`, `SECURITY.md`, `docs/DATABASE.md`, `README.md`, `CHANGELOG.md` e `docs/PROJECT_STATE.md`, conforme o caso.

## Git

- O projeto usa a branch `main`. Cada etapa validada vira um commit pequeno e coerente.
- Mensagens no padrão **Conventional Commits**, por exemplo `feat(api): add GET /events/{id}`, `fix(schemas): ...`, `test(api): ...`, `docs: ...`, `chore: ...`.
- Adicione os arquivos **pelo nome**, e não com `git add .`, para não incluir arquivos que não deveriam ir.
- Nunca versione o `.env`, bancos (`*.db`), cópias deles ou dados reais. A pasta `data/` é ignorada.
- Só envie ao GitHub com os testes passando. Um jeito de garantir isso:

```powershell
cd backend
python -m pytest -q --tb=short
$testesOk = $LASTEXITCODE
cd ..
if ($testesOk -eq 0) {
    git add caminho/do/arquivo
    git commit -m "tipo(escopo): descricao"
    git push
}
```

## Convenções de código

- Tipagem em todas as funções e docstring curta em cada função pública.
- Nomes de código em inglês. Comentários e documentação em português.
- Configuração por variáveis de ambiente, nunca valores fixos no código.
- Em Python, `\u` seguido de números dentro de um texto comum é uma **instrução** para criar aquele caractere. Um "surrogate" solto (de U+D800 a U+DFFF) em uma docstring impede o arquivo de ser importado. Em docstrings e comentários, descreva o caractere como `U+D800`.

## Armadilhas do Windows PowerShell 5.1

| Situação | O que fazer |
|---|---|
| Gravar arquivo de texto com acentos | Use `[System.IO.File]::WriteAllText(caminho, texto, (New-Object System.Text.UTF8Encoding($false)))`. O `>` e o `Out-File` padrão gravam em UTF-16 ou com BOM |
| Gravar o `requirements.txt` | Use `python -m pip freeze \| Out-File -Encoding ascii backend\requirements.txt` |
| Enviar JSON com acentos | Converta o texto em bytes UTF-8 antes (`[System.Text.Encoding]::UTF8.GetBytes(...)`) |
| Acentos errados na tela (por exemplo `JosÃ©`) | É só a exibição. Decodifique a resposta como UTF-8 de forma explícita para conferir |
| Contar os itens de `Invoke-RestMethod` | Guarde o resultado em uma variável (`$lista = Invoke-RestMethod ...; $lista.Count`). `@(Invoke-RestMethod ...).Count` devolve sempre 1 |
| Saídas longas do Git travando em `(END)` | Aperte `q`, ou rode `git config --global core.pager cat` |
| Comandos do Linux | Prefira o equivalente em PowerShell (`Get-ChildItem`, `Select-String`, `Remove-Item`) |

## Mapa da documentação

| Documento | Conteúdo |
|---|---|
| [README.md](../README.md) | Apresentação e primeiros passos |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Organização do código e fluxo de um evento |
| [API.md](API.md) | Endpoints, campos, limites e códigos de resposta |
| [DATABASE.md](DATABASE.md) | Tabela, migrações e operação do banco |
| [SECURITY.md](../SECURITY.md) | Proteções existentes e limitações conhecidas |
| [PROJECT_STATE.md](PROJECT_STATE.md) | Estado detalhado do desenvolvimento |
| [ROADMAP.md](../ROADMAP.md) | Fases do projeto |
| [CHANGELOG.md](../CHANGELOG.md) | Histórico de mudanças |