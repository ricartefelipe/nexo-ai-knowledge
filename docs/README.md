# Documentação

Índice da versão 0.1.0, ainda não publicada. Cada documento descreve o que o repositório contém hoje.

## Operação

- [README](../README.md) — problema, capacidade desta versão, execução, testes e limitações.
- [Changelog](../CHANGELOG.md) — alterações do código. Uma entrada não publica a versão.
- [Contribuir](../CONTRIBUTING.md) — GitFlow, commits e verificações obrigatórias.

## Arquitetura

- [C4](architecture/c4.md) — contexto, contêineres e componentes que existem no processo.
- [Decisões](adr/README.md) — monólito, persistência e subida sem provedor de modelo.

## Código

```text
src/nexo_ai/
  main.py                         composição do processo
  config/                         configuração e logging
  api/                            rotas, erros, correlação e esquemas
  infrastructure/persistence/     engine, sessão e prontidão
migrations/                       Alembic; a revisão inicial habilita pgvector
tests/unit/                       configuração, logging e sondas
tests/api/                        contrato HTTP
tests/integration/                PostgreSQL real
```

Não há pacote de domínio nem de aplicação nesta versão. Essas camadas entram quando houver regra de negócio para proteger.
