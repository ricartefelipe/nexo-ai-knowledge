# Contribuir

## Fluxo de branches

O repositório usa GitFlow. Estes são os únicos nomes aceitos:

| Branch | Origem | Destino da integração |
| --- | --- | --- |
| `main` | release ou hotfix | Estado publicável. Não recebe funcionalidade direta. |
| `develop` | feature, release ou hotfix | Integração do que ainda não foi publicado. |
| `feature/<nome>` | `develop` atualizado | Pull request com base `develop`. |
| `release/<versao>` | `develop` | `main` e, em seguida, `develop`. |
| `hotfix/<nome>` | `main` | `main` e, em seguida, `develop`. |

O nome descreve a mudança. Não inclui ferramenta, editor ou crédito de autoria. A pipeline recusa pull request cuja branch de origem ou de destino fuja dessa tabela.

### Integrar

1. Atualize a branch de origem e crie a branch de trabalho a partir dela.
2. Abra o pull request para o destino da tabela.
3. Integre com merge commit, sem fast-forward, sem squash e sem rebase.
4. No mesmo ato, apague a branch de trabalho, local e remota. Uma branch já mergeada não permanece no repositório.

Para uma feature integrada pelo GitHub:

```bash
git checkout develop
git pull origin develop
git branch -d feature/<nome>
git push origin --delete feature/<nome>
```

Para integrar localmente:

```bash
git checkout develop
git pull origin develop
git merge --no-ff feature/<nome>
git push origin develop
git branch -d feature/<nome>
git push origin --delete feature/<nome>
```

`release/*` e `hotfix/*` seguem a mesma exclusão depois de terem voltado para `main` e para `develop`. Não reutilize o nome de uma branch já apagada; crie outra a partir da origem atualizada.

Não use force push, rebase destrutivo ou reset para descartar histórico publicado.

A proteção de `main` e `develop`, com revisão e checks obrigatórios, deve ser configurada no GitHub quando o proprietário autorizar a alteração remota. Este repositório documenta a política; a configuração remota não é aplicada automaticamente.

## Commits

Use Conventional Commits. Cada commit deve ser pequeno e tratar de uma alteração coesa.

Exemplos:

```text
feat(api): add readiness check
fix(persistence): keep the vector extension on failed downgrade
test(api): cover problem details for unexpected errors
docs(architecture): record the persistence decision
```

Antes de gravar o commit:

1. Confirme a branch.
2. Revise o diff e adicione arquivos individualmente.
3. Procure segredos, credenciais reais e artefatos temporários.
4. Execute formatação, lint, tipagem e os testes pertinentes.
5. Escreva a mensagem no imperativo, sem assinatura, sem `Co-authored-by` e sem `Signed-off-by`.

Não use `git add .` nem `git add -A`.

## Qualidade

Na raiz do repositório, com o banco local disponível para a suíte completa:

```bash
uv sync --frozen --all-groups
uv run ruff format --check
uv run ruff check
uv run mypy
uv run pytest --cov-fail-under=85
uv run pip-audit --progress-spinner off
```

Não neutralize falha com `|| true` e não reduza a cobertura para contornar um teste ausente.

## Configuração e segredos

Copie `.env.example` para `.env`. O arquivo `.env` permanece fora do Git. Não grave senha, token ou URL de produção no código, na pipeline ou na documentação.

A fundação aceita subir sem provedor de LLM. Quando uma função depender de configuração ausente, ela deve falhar de forma explícita.
