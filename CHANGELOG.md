# Changelog

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). A tag `v0.4.0` é a primeira publicação. As versões 0.1.0, 0.2.0 e 0.3.0 fazem parte dessa tag e não receberam tag própria.

## [0.5.0] - 2026-10-29

### Added

- `API_AUTH_TOKEN`: token compartilhado aceito em `Authorization: Bearer` ou `X-Api-Key`, exigido nas rotas de documentos, consultas e na página. Obrigatório fora do perfil local ao escutar em todas as interfaces e sempre em produção, com no mínimo 32 caracteres.
- `support` e `sources_found` na resposta de consulta: `supported`, `unsupported` ou `no_sources`. `grounded` só é verdadeiro quando a resposta cita uma fonte devolvida e compartilha termos com ela.
- `DELETE /api/v1/documents/{id}` remove documento, fragmentos e vetores.
- Migration `0003`: colunas `embedding_model` e `chunking_version` em documentos. A busca compara somente vetores do modelo configurado; a reingestão com outro modelo recalcula os vetores.
- Readiness informa `database`, `embedding_provider`, `completion_provider` e `embedding_model`.
- CI: job `image` constrói a imagem final, bloqueia HIGH/CRITICAL no Trivy e faz um smoke contra PostgreSQL com token.

### Changed

- Imagem final em `python:3.12-alpine`, com `apk upgrade` e sem pip, setuptools e wheel em runtime.
- `pypdf` 6.21.4.
- O prompt do modelo de linguagem exige a citação `[n]`.

## [0.4.2] - 2026-10-12

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
