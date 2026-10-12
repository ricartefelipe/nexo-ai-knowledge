# Nexo AI

Uma plataforma inteligente que transforma informações dispersas em conhecimento acessível, ajudando pessoas e equipes a encontrar respostas, compreender decisões e consultar fontes confiáveis.

Nesta versão, **0.3.0 ainda não publicada**, o repositório entrega a fundação, a ingestão de documentos e a consulta em linguagem natural com fontes verificáveis. A 0.1.0 e a 0.2.0 estão integradas em `develop` e também não foram publicadas.

## Problema

Informações organizacionais ficam espalhadas em documentos e registros. Pessoas e equipes precisam de um lugar para consultar esse conhecimento com rastreabilidade. A fundação prepara a persistência e o processo da aplicação para que os incrementos seguintes possam indexar documentos e responder com fontes verificáveis.

## O que esta versão faz

- Sobe uma API FastAPI sem exigir credencial de modelo de linguagem.
- Valida a configuração do processo antes de atender requisições.
- Registra logs JSON com identificador de correlação.
- Responde erros HTTP como problem details (RFC 9457), sem stack trace.
- Executa as migrations, que habilitam a extensão `vector` e criam as tabelas de documento.
- Expõe liveness e readiness com significados distintos.
- Recebe PDF, Markdown e TXT, fragmenta o texto e grava embeddings quando `EMBEDDING_API_KEY` está configurada.
- Persiste o estágio do documento: recebido, extraído, fragmentado, indexado ou falha.
- Responde uma pergunta a partir dos fragmentos indexados e devolve esses fragmentos junto da resposta.

## Arquitetura

O processo é um monólito modular. O ponto de composição é `src/nexo_ai/main.py`. A configuração não depende de FastAPI. A rota de saúde não executa SQL; ela consulta uma sonda de prontidão. A ingestão e a consulta passam pelos casos de uso em `application`. A consulta gera o vetor da pergunta, busca os fragmentos mais próximos pela distância de cosseno e só chama o modelo de linguagem quando existe fonte dentro do limite configurado. As referências saem do banco, não do texto gerado.

O mapa da documentação está em [docs/README.md](docs/README.md). Os diagramas estão em [docs/architecture/c4.md](docs/architecture/c4.md) e as decisões em [docs/adr/README.md](docs/adr/README.md). O fluxo de branches está em [CONTRIBUTING.md](CONTRIBUTING.md).

## Tecnologias

- Python 3.12
- FastAPI, Pydantic e Pydantic Settings
- SQLAlchemy 2 síncrono e psycopg 3
- Alembic
- PostgreSQL 16 com pgvector 0.8.7 e a coluna `vector(1536)`
- pypdf, para texto de PDF
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

O arquivo `.env.example` contém apenas valores locais. A aplicação ignora variáveis desconhecidas. Sem `EMBEDDING_API_KEY`, o processo sobe e a ingestão e a consulta respondem que o provedor de embeddings não está configurado. Sem `COMPLETION_API_KEY`, a consulta responde que o provedor de linguagem não está configurado. As duas chaves são independentes e usam o mesmo `EMBEDDING_BASE_URL`.

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
- `POST /api/v1/documents` — envia um arquivo no campo `file`. PDF, Markdown ou TXT.
- `GET /api/v1/documents/{id}` — mostra o estágio da ingestão, sem o texto dos fragmentos e sem os vetores.
- `POST /api/v1/queries` — corpo `{"question": "..."}`. Responde com `answer`, `grounded` e `references`.

O contrato interativo está em `/docs`.

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS -D - http://127.0.0.1:8000/health/ready
curl -fsS -F "file=@notas.md;type=text/markdown" http://127.0.0.1:8000/api/v1/documents
curl -fsS -H "Content-Type: application/json" \
  -d '{"question":"qual o prazo?"}' \
  http://127.0.0.1:8000/api/v1/queries
```

Quando nenhum fragmento indexado fica dentro de `QUERY_MAX_DISTANCE`, a resposta é `200`, `grounded` é `false`, `references` fica vazio e o modelo de linguagem não é chamado. O texto fixo é `As fontes indexadas não respondem a essa pergunta.` Quando há fonte, cada referência traz `document_id`, `filename`, `position`, `content` e `distance`. A consulta não é gravada.

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
- Não há interface. A consulta é só a API.
- Uma resposta sem fonte próxima não inventa citação.
- PDF digitalizado, sem texto, é recusado. Não há OCR.
- A coluna vetorial está fixada em 1536 dimensões para `text-embedding-3-small`. Não há índice ANN.
- Métricas e OpenTelemetry não estão ativos.
- As credenciais do Compose são de desenvolvimento. Não as reutilize fora da máquina local.
- As versões 0.1.0, 0.2.0 e 0.3.0 ainda não foram publicadas como release.

## Roadmap

1. **v0.4.0 — Experiência:** interface sobre os contratos estáveis da API.

Recuperação híbrida, reranking, autenticação e processamento assíncrono ficam para quando houver requisito concreto.
