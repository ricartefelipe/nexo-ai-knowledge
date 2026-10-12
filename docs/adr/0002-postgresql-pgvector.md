# ADR 0002: PostgreSQL, pgvector e SQLAlchemy síncrono

## Status

Aceito. A 0.2.0 acrescentou as tabelas de documento e a coluna `vector(1536)`. A 0.3.0 consulta essa coluna pela distância de cosseno, sem migration nova. A escolha de PostgreSQL, pgvector e SQLAlchemy síncrono permanece. Veja a [ADR 0005](0005-grounded-retrieval.md).

## Contexto

A recuperação de conhecimento vai precisar de metadados relacionais e de busca por similaridade. A fundação precisa escolher a fonte de verdade e provar que a extensão vetorial sobe por migration, antes de existir coluna de embedding.

A dimensão do vetor depende do modelo de embedding, que ainda não foi selecionado. Fixá-la agora criaria uma migration destinada a ser desfeita.

## Decisão

PostgreSQL 16 com a imagem `pgvector/pgvector:0.8.7-pg16` é a fonte de verdade local. A migration `0001_enable_pgvector` executa `CREATE EXTENSION IF NOT EXISTS vector` e não cria tabela de negócio.

O acesso usa SQLAlchemy 2 síncrono e o driver `postgresql+psycopg`. O engine configura `pool_size`, `max_overflow`, `pool_timeout`, `pool_pre_ping` e `connect_timeout`. A sessão é aberta pela factory criada na subida e fechada por quem a utiliza. A sonda de prontidão abre uma conexão curta, executa `SELECT 1` e consulta `pg_extension`.

O downgrade executa `DROP EXTENSION IF EXISTS vector` sem `CASCADE`. Se houver objeto dependente, o PostgreSQL recusa a remoção e a extensão permanece.

## Consequências

A v0.2.0 pode adicionar tabelas e uma coluna `vector(n)` quando o modelo e a dimensão estiverem escolhidos. Uma mudança de dimensão exigirá migration explícita, não um ajuste implícito de configuração.

O processo não paga a complexidade de sessão assíncrona enquanto o trabalho for configuração, SQL curto e health check. A ingestão, que fará I/O de arquivo e de embedding, pode rever essa escolha com uma ADR nova.

Testes de persistência usam PostgreSQL real. SQLite não representa a extensão `vector` e não substitui esses testes.

## Alternativas

- SQLAlchemy assíncrono com asyncpg. Adiado: a fundação não tem I/O longo e a sessão síncrona é mais simples de transacionar e testar.
- Banco vetorial separado. Rejeitado neste estágio: dois armazenamentos sem um fluxo de indexação aumentam a chance de metadados e vetores divergirem.
- Criar a coluna de embedding com uma dimensão provisória. Rejeitado: a dimensão é parte do contrato físico e ainda não há modelo selecionado.
