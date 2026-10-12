# ADR 0005: Consulta fundamentada nos fragmentos indexados

## Status

Aceito. A interface chegou na 0.4.0 e consome esta consulta sem alterar o contrato. Veja a [ADR 0006](0006-local-interface.md).

## Contexto

A ingestão grava `vector(1536)` em `document_chunks` e deixa o documento em `embedded`. A consulta precisa responder em linguagem natural e mostrar a origem de cada trecho usado. O corpus desta versão cabe numa varredura exata. Não há requisito de interface, de autenticação nem de gravar o histórico das perguntas.

A [ADR 0004](0004-document-ingestion.md) fixou o modelo de embeddings e adiou o framework. A [ADR 0003](0003-startup-without-llm.md) exige que a ausência de chave falhe na operação, sem impedir a subida do processo.

## Decisão

`POST /api/v1/queries` recebe `{"question": "..."}`. O caso de uso gera um vetor da pergunta com o mesmo cliente e a mesma dimensão da ingestão. A busca usa o operador de distância de cosseno `<=>` somente em documentos `embedded` cujo fragmento tem embedding. O padrão aceita distância até `0.5` e devolve no máximo cinco fragmentos, do mais próximo ao mais distante.

Sem fragmento dentro do limite, a resposta HTTP é `200`, `grounded` é `false`, `references` fica vazio e o texto é fixo: `As fontes indexadas não respondem a essa pergunta.` O modelo de linguagem não é chamado nesse caminho.

Com fonte, o processo chama `POST {EMBEDDING_BASE_URL}/chat/completions`, modelo padrão `gpt-4o-mini`, temperatura `0`. O prompt pede resposta em português restrita às fontes numeradas. As referências da resposta HTTP são as linhas lidas do banco (`document_id`, `filename`, `position`, `content`, `distance`), não um trecho interpretado da resposta do modelo.

`COMPLETION_API_KEY` é independente de `EMBEDDING_API_KEY`. As duas usam `EMBEDDING_BASE_URL`. Sem uma delas, a consulta responde que o provedor correspondente não está configurado. O processo continua subindo. A pergunta não é persistida. Não há migration nova nem índice ANN.

A chamada HTTP fica no cliente de infraestrutura. Não há LangChain neste fluxo.

## Consequências

Uma resposta sem fonte próxima não inventa citação. Uma resposta com fonte continua dependente do modelo para o texto, e o chamador confere o conteúdo devolvido em `references`.

Trocar o modelo de embeddings continua exigindo outra migration, como na ingestão. Um corpus maior pode precisar de índice ANN; esta versão não o cria porque a varredura exata é suficiente e previsível.

A interface continua fora. Ela é a v0.4.0.

## Alternativas

- Ler citações do texto gerado pelo modelo. Rejeitado: o modelo pode citar um arquivo que não estava entre os fragmentos selecionados.
- Reusar `EMBEDDING_API_KEY` quando `COMPLETION_API_KEY` estiver vazia. Rejeitado: as credenciais podem ser distintas e a ausência deve falhar de forma explícita.
- Gravar cada pergunta. Rejeitado: não há requisito de auditoria de consulta nesta versão.
- Índice HNSW ou IVFFlat agora. Rejeitado: o volume não justifica aproximação.
- LangChain para o fluxo de recuperação. Rejeitado: a busca SQL e a chamada HTTP permanecem pequenas e testáveis sem o framework.
