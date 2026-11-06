# 007 · Melhoria na escolha dos cortes (2026-11-06)

Problema: o corte 1 da amostra caiu na abertura do evento (saudações e apresentações).

Mudanças em `apps/engine/src/garimpo/cortes.py` (sem LLM, rápido em CPU):
- vocabulário raro na palestra inteira (TF-IDF) no lugar da contagem dentro do tema;
- gancho (primeira frase não começa com "e", "mas", "então"...);
- conteúdo concreto (números, perguntas, marcadores como "na prática", "ou seja", "regra");
- penalidade para saudações, agradecimentos e passagem de palavra;
- penalidade para os 3 primeiros e 3 últimos minutos da gravação;
- vários cortes por tema longo (1 a cada 7 min de tema), sem sobreposição.

Resultado na amostra de 15 min: os 3 cortes saíram de 3:23, 6:28 e 13:07; a saudação do início deixou de ser escolhida. O corte 1 ainda fala do formato do debate (meta-conversa), então não é o ideal.

Pendente: ranquear os melhores candidatos com um LLM ou embeddings (só nos finalistas, para caber na CPU) e calibrar com cortes que o usuário aprovar ou rejeitar.
