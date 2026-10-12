# Changelog

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). A tag `v0.4.0` é a primeira publicação. As versões 0.1.0, 0.2.0 e 0.3.0 fazem parte dessa tag e não receberam tag própria.

## [Unreleased]

### Changed

- `docker compose up --build` sobe o banco e a API sem criar arquivo.

## [0.4.1] - 2026-10-12

### Added

- `./scripts/start.sh` sobe o banco e a API. As chaves opcionais ficam no `.env`.

## [0.4.0] - 2026-10-12

### Added

- Página local em `/` para indexar um documento, ver o estágio e perguntar com as fontes devolvidas pela API.
- Folha de estilo e script empacotados em `/assets`, sem passo de build e sem serviço separado.

## [0.3.0] - 2026-10-12

### Added

- `POST /api/v1/queries` responde uma pergunta a partir dos fragmentos indexados.
- Busca pelos vizinhos mais próximos com a distância de cosseno em `vector(1536)`.
- Resposta fundamentada com referências lidas do banco. Sem fonte próxima, a resposta não cita nada e o modelo de linguagem não é chamado.

## [0.2.0] - 2026-10-12

### Added

- Ingestão de PDF textual, Markdown e TXT com estados persistidos: recebido, extraído, fragmentado, indexado ou falha.
- Fragmentação determinística e embeddings `vector(1536)` do modelo `text-embedding-3-small`.
- `POST /api/v1/documents` e `GET /api/v1/documents/{id}`.

## [0.1.0] - 2026-10-12

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
