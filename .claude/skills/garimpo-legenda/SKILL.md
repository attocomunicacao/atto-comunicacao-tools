---
name: garimpo-legenda
description: Use ao ajustar a legenda dos cortes do Garimpo — quebra das linhas, escolha da palavra-chave em serifa, ordem de leitura, posição na tela e animação do texto — ou ao revisar o plano de legenda de um corte gerado. Traz as regras (docs/legenda.md), onde cada uma mora e como testar rápido.
---

# Legenda do Garimpo

Regras completas: `docs/legenda.md`. Resumo do que o cliente pediu:
- a palavra em serifa itálica é **a palavra em destaque de sentido** (nunca artigo, preposição, "é", "né");
- as linhas formam frases **na ordem da fala** (acima → chave → abaixo);
- os espaços têm lógica: rosto livre, ilustrações em cima (230–900 px), legenda no terço inferior (1270–1600 px).

## v0.7
- Quebra das linhas: `motion.segmentar` (programação dinâmica; custos em `_custo_quebra`/`_custo_linha`,
  listas `FUNCAO`, `VERBOS_AUX`, `ADJ_ANTES`, `UNIDADES_FALA`). Linha guarda `pont` (pergunta → máquina).
- Visual: `legendas.ts` → `compor` (bloco em escada, entrelinha 0,92, hierarquia S : 1,2S : K) + `viver`
  (deriva e saída em desfoque de 0,16 s). Presets só mudam a entrada (0,3–0,45 s, expo/power out).
  Medidas da referência: docs/pesquisa/2026-11-referencias-v07.md.

## Presets (motor)
Cada linha recebe `preset` em `motion.escolher_presets`: gancho (impacto, revelacao, glitch), maquina (pergunta),
elastico (número), esquerda/direita (contraste), sobe (chave forte), rodízio cinematico/deslocamento/desce.
Implementação visual: `apps/desktop/src/renderer/src/motion/legendas.ts`. A posição vem de `caixa` (mapa de espaço).
Para criar um preset: função em `legendas.ts` + registro em `PRESETS` + regra em `escolher_presets` + teste.

## Onde mexer
| O quê | Arquivo / função |
|---|---|
| Quebra das linhas | `apps/engine/src/garimpo/motion.py` → `grupos_legenda` (MAX_GRUPO, pausas, palavra vazia no fim) |
| Palavra-chave | `chaves_por_llm` (LLM, `PEDIDO_CHAVES`), `_peso_chave` + `AUXILIARES` (reserva), `sem_chave` |
| Layout e motion | `apps/desktop/src/renderer/src/motion/main.ts` → `legenda`, `tamanhoChave`; estilo em `motion.css` (.grupo, .chave, .linha-peq) |

## Testar rápido (sem render)
```bash
cd apps/engine
uv run python - <<'EOF'
import json
from garimpo import motion, juiz
from garimpo.modelos import Palavra
d = json.load(open(r"<projeto>/cortes.json", encoding="utf-8"))[0]
ws = [Palavra(**p) for p in d["palavras"]]
gs = motion.grupos_legenda(ws, ws[0].ini)
motion.chaves_por_llm(juiz.carregar(print).llm, gs); motion.sem_chave(gs)
for g in gs: print(" ".join(f"[{w['t']}]" if w["chave"] else w["t"] for w in g["palavras"]))
EOF
```
Confira: nenhuma linha termina em "de/da/e/que"; chave nunca é palavra vazia; linhas de muleta sem chave.

## Revisar um corte renderizado
Use o agente `legendista` (`.claude/agents/legendista.md`) com o caminho do `corte-NN.plano.json`. Ele lista as linhas
problemáticas e propõe a chave certa; ajustes que se repetem viram regra/teste em `apps/engine/tests/test_motion.py`.

Render rápido depois de mudar só o motion: `ATTO_MANTER_TMP=1` (trechos reenquadrados ficam em cache).
