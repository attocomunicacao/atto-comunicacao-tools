# Seleção "inteligente" de cortes — pesquisa e desenho (2026-11-10, v0.7)

## O que a pesquisa mostra
- Segmentação de tema em fala (podcast) funciona melhor com **embeddings de frase** do que com contagem de
  palavras (TextTiling clássico); a fronteira é o vale de similaridade entre janelas vizinhas
  ([MDPI 2025](https://www.mdpi.com/2076-3417/15/19/10849), [tese Webis 2025](https://downloads.webis.de/theses/papers/chaitanya-valaboju_2025.pdf),
  [arXiv 2307.13394](https://arxiv.org/pdf/2307.13394)).
- Ferramentas de corte (OpusClip, LumiClip) seguem o mesmo funil: transcrever → segmentar temas → pontuar
  candidatos → selecionar sem sobreposição → gancho
  ([LumiClip](https://pulseaugur.com/cluster/30427-lumiclip-ai), [OpusClip](https://www.opus.pro/blog/ai-podcast-clipping-goes-mainstream-video-creators)).
- Modelo de embeddings: **multilingual-e5-small** (MIT, 384 dim, ONNX int8 118 MB, prefixos "query:"/"passage:").

## Desenho no Garimpo
1. `semantica.py` — vetores das frases (cache em `cache/vetores`).
2. `estrutura.estruturar` — frases (quebra falas de 45+ palavras), parágrafos (pausa OU virada de sentido),
   temas (TextTiling 70% sentido + 30% vocabulário).
3. `cortes.sugerir(descricao=, vs=)`:
   - filtro duro de **fechamento** (`fecha_bem`): fim de frase + pausa ≥ 0,45 s + a próxima frase não continua a
     ideia ("porém", "mas", "então", "agora"...), salvo pausa ≥ 1,2 s;
   - **relevância** para a descrição do usuário (z-score do cosseno) e **coesão** (uma ideia só);
   - **juiz** com a frase de ANTES e DEPOIS (contexto e fechamento de verdade) e nota de relevância;
   - **gancho**: abertura com nota < 7 → cold open obrigatório com a oração mais forte e mais **central**.
4. Agente `avaliador-de-cortes` para medir gancho/contexto/fechamento depois (meta: gancho ≥ 7 em 80%).
