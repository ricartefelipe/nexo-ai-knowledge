# Contribuir

## Fluxo de branches

O repositório usa GitFlow.

- `main` conserva o estado publicável. Não recebe desenvolvimento direto.
- `develop` integra funcionalidades concluídas.
- `feature/*` nasce de `develop`.
- `release/*` nasce de `develop` e retorna para `main` e `develop`.
- `hotfix/*` nasce de `main` e retorna para `main` e `develop`.

Integrações previstas usam merge sem fast-forward. Não use force push, rebase destrutivo ou reset para descartar histórico.

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
5. Escreva a mensagem no imperativo, sem assinatura adicional.

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
