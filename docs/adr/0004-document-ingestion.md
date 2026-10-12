# ADR 0004: Ingestão com estados persistidos

## Status

Aceito. A consulta em linguagem natural chegou na 0.3.0 e não altera esta decisão. Veja a [ADR 0005](0005-grounded-retrieval.md).

## Contexto

A fundação sobe sem provedor e sem tabelas de negócio. A ingestão é o primeiro fluxo com regra: receber um arquivo, extrair texto, fragmentar, gerar embeddings e deixar cada etapa consultável. A dimensão do vetor passa a fazer parte do contrato físico porque o modelo foi escolhido.

Não há consulta em linguagem natural nesta versão. Também não há fila, serviço separado nem interface.

## Decisão

`POST /api/v1/documents` aceita um arquivo PDF, Markdown ou TXT de até 10 MiB. O nome gravado é só o último segmento do caminho. PDF protegido, PDF sem texto, arquivo vazio, tipo não aceito e texto fora de UTF-8 falham antes de existir linha no banco.

O caso de uso grava o documento em `received`, `extracted`, `chunked` e `embedded`. Uma falha depois da gravação inicial fica em `failed`, com uma mensagem fixa, e um novo envio dos mesmos bytes retoma esse registro. Os mesmos bytes já indexados devolvem o registro existente.

A fragmentação é uma janela de caracteres com sobreposição. Quando cabe, o corte usa a última quebra de linha ou o último espaço da segunda metade da janela. Não há tokenizador de modelo.

Os vetores usam `vector(1536)`, a dimensão de `text-embedding-3-small`. A migration fixa essa dimensão. Trocar o modelo exige outra migration. O cliente HTTP fala com a API compatível em `EMBEDDING_BASE_URL`; a chave fica de fora dos logs e das respostas. Sem `EMBEDDING_API_KEY`, o processo sobe e a ingestão responde que o provedor não está configurado, sem gravar o arquivo.

A resposta HTTP não devolve o texto dos fragmentos nem os vetores. `GET /api/v1/documents/{id}` mostra o estágio, a contagem e o detalhe de falha.

## Consequências

A v0.3.0 pode consultar `document_chunks.embedding` sem redefinir a coluna, desde que continue no mesmo modelo. Uma falha do provedor deixa fragmentos sem vetor e o documento em `failed`.

O processo continua síncrono. O volume atual cabe numa requisição; fila e execução assíncrona continuam fora até haver um requisito concreto.

## Alternativas

- Vetor de dimensão configurável. Rejeitado: a coluna e o provedor divergiriam sem uma migration.
- Embeddings simulados no código de produção. Rejeitado: a versão passaria a declarar uma capacidade que o provedor não executou.
- LangChain neste fluxo. Adiado: a fragmentação e a chamada HTTP são pequenas e testáveis sem o framework. A recuperação pode reavaliar isso.
