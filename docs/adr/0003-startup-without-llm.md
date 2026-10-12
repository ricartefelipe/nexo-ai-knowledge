# ADR 0003: A aplicação sobe sem provedor de LLM

## Status

Aceito. A ingestão da 0.2.0 falha de forma explícita quando falta a chave de embeddings. A consulta da 0.3.0 faz o mesmo para embeddings e para `COMPLETION_API_KEY`. Nenhuma das duas impede a subida do processo. Veja a [ADR 0005](0005-grounded-retrieval.md).

## Contexto

A fundação precisa ser executável em desenvolvimento e na pipeline sem segredo externo. A geração de respostas e os embeddings entram em versões posteriores. Inicializar um cliente de modelo no startup acoplaria a saúde do processo a uma credencial que esta versão não usa.

OpenTelemetry automático do FastAPI 0.143 passou a ser opt-in. Não há fluxo de ingestão ou consulta cuja latência justifique um coletor agora. O identificador de correlação e o log JSON cobrem o diagnóstico das rotas existentes.

## Decisão

Nenhuma configuração de provedor é lida na v0.1.0. A ausência de chave não impede o processo de subir. A descrição da API declara que o uso previsto é local e sem autenticação.

O FastAPI é construído sem ativar a exportação automática de telemetria. Não há cliente de métricas.

Quando a recuperação for implementada, a chamada ao provedor ficará atrás de um contrato da aplicação. Configuração ausente deverá falhar na operação que depende dela, com erro explícito, sem derrubar a liveness do processo.

## Consequências

Os health checks e a migration podem ser validados sem rede externa além da imagem do banco. A v0.3.0 terá de acrescentar configuração, timeout e tratamento de falha do provedor sem reaproveitar um cliente global inexistente.

Não há métrica de token, latência de embedding ou latência de modelo porque essas operações não existem.

## Alternativas

- Exigir uma chave e falhar no startup. Rejeitado: bloquearia a fundação e incentivaria o commit de uma credencial falsa.
- Embutir um modelo local ou respostas simuladas. Rejeitado: simularia uma capacidade que a versão não entrega.
- Subir um coletor OpenTelemetry no Compose. Rejeitado: adicionaria um contêiner sem operação relevante para medir.
