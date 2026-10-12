# Documentação

Índice da versão 0.2.0, ainda não publicada. Cada documento descreve o que o repositório contém hoje.

## Operação

- [README](../README.md) — problema, capacidade desta versão, execução, testes e limitações.
- [Changelog](../CHANGELOG.md) — alterações do código. Uma entrada não publica a versão.
- [Contribuir](../CONTRIBUTING.md) — GitFlow, commits e verificações obrigatórias.

## Arquitetura

- [C4](architecture/c4.md) — contexto, contêineres e componentes que existem no processo.
- [Decisões](adr/README.md) — monólito, persistência, subida sem provedor e ingestão.

## Código

```text
src/nexo_ai/
  main.py                         composição do processo
  domain/                         documento, fragmentos e transições de estado
  application/                    caso de uso de ingestão
  config/                         configuração e logging
  api/                            rotas, erros, correlação e esquemas
  infrastructure/                 extração, embeddings, engine e prontidão
migrations/                       Alembic; pgvector e tabelas de documento
tests/unit/                       regras, extração e cliente de embeddings
tests/api/                        contrato HTTP
tests/integration/                PostgreSQL real
```

Não há pacote de domínio nem de aplicação nesta versão. Essas camadas entram quando houver regra de negócio para proteger.
