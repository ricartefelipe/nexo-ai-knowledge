# ADR 0006: Interface local no mesmo processo

## Status

Aceito

## Contexto

A API já recebe documentos, mostra o estágio da ingestão e responde perguntas com referências lidas do banco. A v0.4.0 precisa de uma interface sobre esses contratos, sem abrir autenticação, lista de acervo, fila ou um segundo serviço.

A [ADR 0001](0001-modular-monolith.md) mantém um único processo. A [ADR 0005](0005-grounded-retrieval.md) fixa o formato da consulta.

## Decisão

`GET /` devolve uma página HTML. O CSS e o JavaScript saem de `/assets/app.css` e `/assets/app.js`, arquivos empacotados com o processo. Não há passo de build nem framework. Essas rotas ficam fora do OpenAPI.

O navegador chama `GET /health/ready`, `POST /api/v1/documents` e `POST /api/v1/queries`. O envio já devolve o estágio do documento, então a página não precisa de outra consulta. O texto vindo da API entra na página por `textContent`. A política de conteúdo recusa script e estilo inline.

A página mostra o último documento enviado e a última resposta. Não há lista do acervo, porque a API não oferece essa consulta. A pergunta continua sem persistência.

## Consequências

Quem usa o navegador local vê o mesmo erro e as mesmas fontes que a API devolveria. Mudar o contrato HTTP exige mudar a página no mesmo incremento.

A imagem continua com um processo. Os três arquivos entram no pacote instalado, inclusive na instalação não editável usada pelo contêiner.

## Alternativas

- Aplicação separada. Rejeitado: criaria outro serviço sem requisito operacional.
- Renderizar a resposta no servidor, sem o navegador chamar a API. Rejeitado: a interface deixaria de exercer o contrato HTTP.
- Framework com build. Rejeitado: o fluxo cabe em uma página e aumentaria a cadeia de ferramentas.
