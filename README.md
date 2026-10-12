# Nexo AI

Uma plataforma inteligente que transforma informações dispersas em conhecimento acessível, ajudando pessoas e equipes a encontrar respostas, compreender decisões e consultar fontes confiáveis.

Nesta versão, **0.1.0 ainda não publicada**, o repositório entrega a fundação executável: configuração validada, API HTTP, PostgreSQL com pgvector, logging estruturado e verificações de saúde. Ainda não há ingestão de documentos, busca semântica nem geração de respostas.

## Problema

Informações organizacionais ficam espalhadas em documentos e registros. Pessoas e equipes precisam de um lugar para consultar esse conhecimento com rastreabilidade. A fundação prepara a persistência e o processo da aplicação para que os incrementos seguintes possam indexar documentos e responder com fontes verificáveis.

## O que esta versão faz

- Sobe uma API FastAPI sem exigir credencial de modelo de linguagem.
- Valida a configuração do processo antes de atender requisições.
- Registra logs JSON com identificador de correlação.
- Responde erros HTTP como problem details (RFC 9457), sem stack trace.
- Executa a migration inicial, que habilita a extensão `vector` no PostgreSQL.
- Expõe liveness e readiness com significados distintos.

## Arquitetura

O processo é um monólito modular. O ponto de composição é `src/nexo_ai/main.py`. A configuração não depende de FastAPI. A rota de saúde não executa SQL; ela consulta uma sonda de prontidão. A sonda e o engine SQLAlchemy ficam na infraestrutura.

Não há pacote de domínio nesta versão. As regras de documento, fragmento e consulta entram na ingestão, quando existir invariante de negócio para proteger.

Os diagramas e as decisões estão em [docs/architecture/c4.md](docs/architecture/c4.md) e em [docs/adr](docs/adr).

## Tecnologias

- Python 3.12
- FastAPI, Pydantic e Pydantic Settings
- SQLAlchemy 2 síncrono e psycopg 3
- Alembic
- PostgreSQL 16 com pgvector 0.8.7
- structlog
- uv 0.13
- pytest, Ruff e Mypy
- Docker Compose

As versões resolvidas estão em `uv.lock`.

## Pré-requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/) 0.13 ou superior
- Docker com Docker Compose, para o banco e para a execução containerizada

## Configuração

```bash
uv sync --frozen --all-groups
cp .env.example .env
```

O arquivo `.env.example` contém apenas credenciais locais. A aplicação ignora variáveis desconhecidas e não lê chave de LLM.

`APP_ENV=production` recusa URL de banco sem host ou senha e recusa escutar em todas as interfaces. O padrão de desenvolvimento escuta em `127.0.0.1`.

## Execução local

Subir a API e o PostgreSQL:

```bash
docker compose up --build
```

A API fica em `http://127.0.0.1:8000`. O banco fica em `127.0.0.1:5432`, com usuário, senha e base `nexo`. Essas credenciais servem somente ao ambiente local reproduzível.

O contêiner da API aplica `alembic upgrade head` antes de escutar. O healthcheck da imagem consulta `/health/live`. O healthcheck do Compose consulta `/health/ready`.

Para rodar o processo no host, com o banco do Compose já saudável:

```bash
uv run alembic upgrade head
uv run python -m nexo_ai
```

## API

Não há autenticação. Esta API não está pronta para exposição pública.

- `GET /health/live` — o processo responde. Não consulta o banco.
- `GET /health/ready` — o PostgreSQL responde e a extensão `vector` está instalada.

O contrato interativo está em `/docs`.

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS -D - http://127.0.0.1:8000/health/ready
```

O cabeçalho `X-Request-ID` é aceito quando contém de 1 a 128 caracteres seguros. Caso contrário, a aplicação gera um UUID e o devolve na resposta. O mesmo identificador entra nos logs da requisição.

Erros usam `application/problem+json`. Uma falha interna devolve uma mensagem genérica. O corpo não inclui traceback, senha ou URL do banco.

Readiness indisponível responde `503`:

```json
{
  "type": "about:blank",
  "title": "Service Unavailable",
  "status": 503,
  "detail": "O banco de dados está indisponível.",
  "instance": "/health/ready"
}
```

## Testes e qualidade

A suíte completa exige PostgreSQL local com pgvector. O host aceito é `localhost`, `127.0.0.1`, `::1` ou `db`.

```bash
docker compose up -d db
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://nexo:nexo@127.0.0.1:5432/nexo
uv run ruff format --check
uv run ruff check
uv run mypy
uv run pytest --cov-fail-under=85
uv run pip-audit --progress-spinner off
```

Os testes de integração aplicam a migration, verificam a extensão, consultam a readiness e comprovam que o downgrade sem `CASCADE` falha enquanto existir uma coluna `vector`. A suíte restaura a extensão ao final.

A cobertura exigida é 85% do pacote `nexo_ai`, com medição de ramos, sem omissão de módulos. O percentual medido deve ser lido no relatório do pytest, não neste documento.

O hook local de pre-commit executa o Ruff do ambiente:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Limitações

- Não há autenticação, autorização nem multitenancy.
- Não há upload, extração, fragmentação, embeddings, busca ou resposta fundamentada.
- A migration ainda não cria tabelas de negócio e não fixa a dimensão dos embeddings.
- Métricas e OpenTelemetry não estão ativos.
- As credenciais do Compose são de desenvolvimento. Não as reutilize fora da máquina local.
- A versão 0.1.0 descrita aqui ainda não foi publicada como release.

## Roadmap

1. **v0.2.0 — Ingestão:** receber PDF textual, Markdown e TXT, fragmentar, gerar embeddings e persistir com estados verificáveis.
2. **v0.3.0 — Recuperação:** consulta em linguagem natural, busca vetorial e resposta com referências verificáveis.
3. **v0.4.0 — Experiência:** interface sobre os contratos estáveis da API.

Recuperação híbrida, reranking, autenticação e processamento assíncrono ficam para quando houver requisito concreto.
