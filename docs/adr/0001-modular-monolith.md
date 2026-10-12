# ADR 0001: Monólito modular sem domínio vazio

## Status

Aceito. A 0.1.0 não tinha pacote de domínio. A 0.2.0 criou `domain` e `application` para a ingestão. A 0.3.0 acrescentou a consulta no mesmo processo. A decisão do monólito permanece. Veja a [ADR 0005](0005-grounded-retrieval.md).

## Contexto

O Nexo AI vai ingerir documentos e responder com fontes verificáveis. A primeira entrega só precisa subir um processo confiável, com persistência versionada e saúde observável. Ainda não há invariante de documento, ciclo de vida de ingestão ou contrato de consulta.

Criar pacotes `domain` e `application` sem regras produziria interfaces sem chamador. Adotar microsserviços, fila ou malha de rede anteciparia operação que o produto ainda não exige.

## Decisão

A fundação é um único processo Python. A composição fica em `nexo_ai.main`. A configuração é independente do framework HTTP. A rota de readiness depende de uma sonda, e a implementação dessa sonda permanece na infraestrutura de persistência.

O pacote de domínio e os casos de uso serão introduzidos na ingestão, quando houver entidade, estado e regra para testar. Até lá, a API pode chamar a sonda de persistência diretamente.

## Consequências

A estrutura atual é menor e o caminho de uma requisição de saúde é rastreável. A v0.2.0 precisará criar o agregado de documento e os casos de uso sem reescrever o processo, o banco ou o contrato de saúde.

A rota conhece o protocolo da sonda. Isso é acoplamento aceito nesta versão e deve parar na borda da infraestrutura quando os casos de uso existirem.

## Alternativas

- Esqueleto hexagonal completo, com portas sem implementação de negócio. Rejeitado: adiciona abstração sem reduzir acoplamento real.
- Microsserviços desde a fundação. Rejeitado: o problema atual cabe em um processo e um banco.
