# Changelog

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). As versões abaixo descrevem o estado do código. Uma entrada aqui não significa que a tag ou a release tenha sido publicada.

## [0.1.0] - Unreleased

### Added

- Aplicação FastAPI com configuração validada por ambiente.
- Logs JSON, identificador de correlação e erros HTTP no formato RFC 9457.
- Health checks de liveness e readiness.
- Persistência síncrona com SQLAlchemy 2, psycopg 3 e Alembic.
- Migration inicial que habilita a extensão `vector` no PostgreSQL 16.
- Imagem de container, Compose local e pipeline de qualidade e integração.
- Testes de unidade, API e integração com PostgreSQL e pgvector.

### Changed

- O fluxo de contribuição aceita somente `feature/*`, `release/*` e `hotfix/*`, integra com merge commit e apaga a branch de trabalho depois do merge.

### Fixed

- Falha não tratada registra somente o tipo da exceção. A mensagem não entra no log nem na resposta.
