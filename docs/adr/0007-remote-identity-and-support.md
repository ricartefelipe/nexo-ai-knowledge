# ADR 0007: Identidade por token no modo remoto e status de sustentação

## Status

Aceito

## Contexto

As ADRs [0003](0003-startup-without-llm.md) e [0006](0006-local-interface.md) declaravam o uso local e sem autenticação. A v0.5.0 precisa permitir que o processo escute fora do loopback sem expor o acervo, e precisa distinguir uma resposta sustentada pelas fontes de uma resposta que apenas recebeu fontes.

## Decisão

- Um token compartilhado (`API_AUTH_TOKEN`) protege as rotas de documentos, consultas e a página. No perfil local sem token, o comportamento anterior é mantido. Fora do perfil local, escutar em todas as interfaces sem token é recusado na inicialização; em produção o token é sempre obrigatório, com no mínimo 32 caracteres. A comparação é em tempo constante. As rotas de saúde ficam abertas.
- A resposta de consulta informa `support`: `no_sources` quando nenhum fragmento fica dentro da distância máxima, `unsupported` quando houve fontes mas a resposta não cita `[n]` válido ou não compartilha termos com a fonte citada, e `supported` caso contrário. `grounded` é verdadeiro somente em `supported`. A verificação é lexical e acontece no domínio, sem rede.
- O documento registra `embedding_model` e `chunking_version`. A busca compara somente vetores do modelo configurado. Reingerir com outro modelo recalcula os vetores.
- `DELETE /api/v1/documents/{id}` remove documento, fragmentos e vetores na mesma transação.

## Consequências

- Não há usuários, papéis nem multitenancy. Quem tem o token acessa todo o acervo. Rotação exige reiniciar o processo.
- Uma resposta `supported` cita a fonte e compartilha termos com ela; isso não garante interpretação correta. Uma resposta correta sem citação é classificada como `unsupported`.
- Trocar `EMBEDDING_MODEL` oculta os documentos antigos da busca até a reingestão.
