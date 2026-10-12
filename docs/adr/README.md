# Decisões de arquitetura

Uma decisão aceita descreve o código desta versão. Quando uma decisão mudar, o arquivo antigo permanece e o status passa a registrar a substituição. Não apague o histórico da decisão.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-modular-monolith.md) | Monólito modular, sem pacote de domínio vazio | Aceito |
| [0002](0002-postgresql-pgvector.md) | PostgreSQL 16, pgvector e SQLAlchemy síncrono | Aceito |
| [0003](0003-startup-without-llm.md) | A aplicação sobe sem provedor de modelo | Aceito |
| [0004](0004-document-ingestion.md) | Ingestão com estados persistidos e embeddings | Aceito |
| [0005](0005-grounded-retrieval.md) | Consulta fundamentada nos fragmentos indexados | Aceito |
