# Documentação

Índice da versão 0.3.0, ainda não publicada. Cada documento descreve o que o repositório contém hoje.

## Operação

- [README](../README.md) — problema, capacidade desta versão, execução, testes e limitações.
- [Changelog](../CHANGELOG.md) — alterações do código. Uma entrada não publica a versão.
- [Contribuir](../CONTRIBUTING.md) — GitFlow, commits e verificações obrigatórias.

## Arquitetura

- [C4](architecture/c4.md) — contexto, contêineres e componentes que existem no processo.
- [Decisões](adr/README.md) — monólito, persistência, subida sem provedor, ingestão e consulta fundamentada.

## Código

```text
src/nexo_ai/
  main.py                         composição do processo
  domain/                         documento, fragmentos e resposta fundamentada
  application/                    ingestão e consulta
  config/                         configuração e logging
  api/                            rotas, erros, correlação e esquemas
  infrastructure/                 extração, embeddings, linguagem, engine e prontidão
migrations/                       Alembic; pgvector e tabelas de documento
tests/unit/                       regras, extração, embeddings e linguagem
tests/api/                        contrato HTTP
tests/integration/                PostgreSQL real
```
