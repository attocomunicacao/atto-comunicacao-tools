---
name: lab-animacao
description: Use para rodar o laboratório automatizado de animação do Garimpo em ciclos (prompt → varredura → teste → validação) até um horário ou limite de uso — banco de animações de texto, motion, cenas HyperFrames e transições, comparadas com as referências do cliente.
---

# Laboratório automatizado de animação

Peças:
- `apps/engine/src/garimpo/lab.py` — cenários (11 presets de legenda + 7 cenas), render pelo `--render-motion`,
  métricas de fluidez (entrada, saída, salto, tremor, deriva, cobertura), nota 0-10 contra as faixas da referência.
- `docs/animacoes/banco.json` — banco: `animacoes` (última medida + histórico), `ideias` (pesquisa), `rodadas`.
- Agentes: `orquestrador-lab` (1 ciclo), `pesquisador-de-animacao`, `animador`, `avaliador-de-fluidez`.
- Referências: `docs/pesquisa/2026-11-referencias-v07.md` e os vídeos em `Downloads/videoplayback*.mp4`.

Ciclo contínuo: rode o `orquestrador-lab` repetidamente. Cada ciclo deve terminar com commit ou revert — nunca
deixar a árvore suja. Antes de parar (horário/limite), escreva o resumo no fim de `docs/animacoes/diario-lab.md`
para o próximo ciclo retomar de onde parou.

Rodar à mão: `cd apps/engine && uv run python -m garimpo.lab [nomes] --nota "texto"`; `--listar`.
