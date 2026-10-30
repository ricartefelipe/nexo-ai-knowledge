# Nexo AI

Uma plataforma inteligente que transforma informações dispersas em conhecimento acessível, ajudando pessoas e equipes a encontrar respostas, compreender decisões e consultar fontes confiáveis.

Nesta versão, **0.5.0**, o repositório entrega a fundação, a ingestão, a consulta com fontes verificáveis, a interface local, a identidade por token para o modo remoto, o status de sustentação da resposta e a exclusão de documentos. O arranque é `docker compose up --build`, sem criar arquivo. A 0.1.0, a 0.2.0 e a 0.3.0 fazem parte da tag `v0.4.0` e não têm tag própria.

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
- Serve uma página local em `/` para enviar documentos, consultar o estágio e fazer perguntas. A página chama a API no mesmo processo.
- Exige um token (`API_AUTH_TOKEN`) nas rotas de documentos, consultas e na página quando o processo é exposto fora do perfil local.
- Classifica cada resposta como `supported`, `unsupported` ou `no_sources`, conferindo a citação `[n]` e a sobreposição com as fontes.
- Exclui um documento com seus fragmentos e vetores.
- Registra o modelo de embedding e a versão de fragmentação de cada documento; a busca só compara vetores do modelo configurado.

## Arquitetura

O processo é um monólito modular. O ponto de composição é `src/nexo_ai/main.py`. A configuração não depende de FastAPI. A rota de saúde não executa SQL; ela consulta uma sonda de prontidão. A ingestão e a consulta passam pelos casos de uso em `application`. A consulta gera o vetor da pergunta, busca os fragmentos mais próximos pela distância de cosseno e só chama o modelo de linguagem quando existe fonte dentro do limite configurado. As referências saem do banco, não do texto gerado. A página em `/` é HTML, CSS e JavaScript empacotados no processo; o navegador usa os mesmos contratos HTTP.

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

- Docker com Docker Compose
- Python 3.12 e [uv](https://docs.astral.sh/uv/) 0.13 ou superior, somente para rodar a API fora do contêiner ou para executar a suíte

## Início

Na raiz do repositório, sem criar arquivo:

```bash
docker compose up --build
```

A interface fica em `http://127.0.0.1:8000/`. O mesmo comando está em `./scripts/start.sh`. O contêiner aplica as migrations. Sem chave de provedor, a página abre e a operação que precisar de chave avisa isso.

## Modos de execução

- **Local** (`APP_ENV=local`, padrão do Compose): sem token, a API atende somente quem chega ao processo. Com `API_AUTH_TOKEN` definido, o token passa a ser exigido.
- **Remoto** (`APP_ENV=test` ou `production` escutando em `0.0.0.0` ou `::`): `API_AUTH_TOKEN` é obrigatório. O processo recusa iniciar sem ele.
- `APP_ENV=production` também recusa URL de banco sem host ou senha, recusa escutar em todas as interfaces e exige token com pelo menos 32 caracteres.

O token é enviado em `Authorization: Bearer <token>` ou `X-Api-Key: <token>`. Sem token ou com token diferente, a resposta é `401`. As rotas de saúde não exigem token.

## Execução no host

Com o banco do Compose já saudável:

```bash
docker compose up -d db
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run python -m nexo_ai
```

O healthcheck da imagem consulta `/health/live`. O healthcheck do Compose consulta `/health/ready`.

## API

A autenticação é por token compartilhado, descrita em [Modos de execução](#modos-de-execução). Não há usuários, papéis nem multitenancy.

- `GET /` — página local. Não entra no OpenAPI.
- `GET /health/live` — o processo responde. Não consulta o banco.
- `GET /health/ready` — o PostgreSQL responde e a extensão `vector` está instalada. O corpo informa `database`, `embedding_provider`, `completion_provider` (`configured` ou `not_configured`) e `embedding_model`. Provedor ausente não derruba a prontidão: o processo atende, mas ingestão e consulta respondem que o provedor não está configurado.
- `POST /api/v1/documents` — envia um arquivo no campo `file`. PDF, Markdown ou TXT.
- `GET /api/v1/documents/{id}` — mostra o estágio da ingestão, o `embedding_model` e a `chunking_version`, sem o texto dos fragmentos e sem os vetores.
- `DELETE /api/v1/documents/{id}` — remove o documento, os fragmentos e os vetores. Responde `204`; inexistente responde `404`.
- `POST /api/v1/queries` — corpo `{"question": "..."}`. Responde com `answer`, `support`, `grounded`, `sources_found` e `references`.

O contrato interativo está em `/docs`.

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS -D - http://127.0.0.1:8000/health/ready
curl -fsS -F "file=@notas.md;type=text/markdown" http://127.0.0.1:8000/api/v1/documents
curl -fsS -H "Content-Type: application/json" \
  -d '{"question":"qual o prazo?"}' \
  http://127.0.0.1:8000/api/v1/queries
```

`support` distingue três situações. `no_sources`: nenhum fragmento indexado ficou dentro de `QUERY_MAX_DISTANCE`; `sources_found` é `false`, `references` fica vazio e o modelo de linguagem não é chamado. `unsupported`: houve fontes, mas a resposta do modelo não cita `[n]` válido ou não compartilha termos com a fonte citada; `grounded` é `false` e as referências são devolvidas para leitura. `supported`: a resposta cita uma fonte devolvida e compartilha termos com ela; só então `grounded` é `true`. A verificação é lexical, não semântica.

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

A imagem final é construída e escaneada na CI com Trivy; qualquer vulnerabilidade HIGH ou CRITICAL bloqueia. Localmente: `docker build -t nexo-ai:local .` e `trivy image --severity HIGH,CRITICAL --exit-code 1 nexo-ai:local`.

Os testes de integração aplicam a migration, verificam a extensão, consultam a readiness e comprovam que o downgrade sem `CASCADE` falha enquanto existir uma coluna `vector`. A suíte restaura a extensão ao final.

A cobertura exigida é 85% do pacote `nexo_ai`, com medição de ramos, sem omissão de módulos. O percentual medido deve ser lido no relatório do pytest, não neste documento.

O hook local de pre-commit executa o Ruff do ambiente:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Limitações

- A autenticação é um token compartilhado. Não há usuários, papéis nem multitenancy.
- A verificação de sustentação é lexical: cita uma fonte e compartilha termos com ela. Uma resposta pode citar a fonte e ainda assim interpretá-la mal.
- A troca de `EMBEDDING_MODEL` exige reindexar: documentos de outro modelo deixam de aparecer na busca e ficam identificados em `embedding_model`.
- A interface não lista o acervo. Ela mostra o documento enviado nesta página e a resposta da pergunta.
- Uma resposta sem fonte próxima não inventa citação.
- PDF digitalizado, sem texto, é recusado. Não há OCR.
- A coluna vetorial está fixada em 1536 dimensões para `text-embedding-3-small`. Não há índice ANN.
- Métricas e OpenTelemetry não estão ativos.
- As credenciais do Compose são de desenvolvimento. Não as reutilize fora da máquina local.
- A tag atual é `v0.5.0`. As tags `v0.4.0`, `v0.4.1` e `v0.4.2` continuam publicadas. As versões 0.1.0, 0.2.0 e 0.3.0 não têm tag própria.

## Roadmap

Recuperação híbrida, reranking, usuários com papéis e processamento assíncrono ficam para quando houver requisito concreto. Não há próximo incremento aberto.
