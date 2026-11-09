---
name: garimpo-cortes
description: Use ao ajustar a escolha dos cortes do Garimpo (quais trechos viram vídeo, gancho dos 5 primeiros segundos, cold open, bastidor de gravação, contexto, duração até 90 s) ou a transcrição. Explica as 3 camadas (filtros, heurística, juiz LLM), onde cada regra mora e como validar com um projeto real.
---

# Seleção de cortes do Garimpo

## Pipeline (apps/engine/src/garimpo)
1. `transcricao.py` — Whisper large-v3-turbo, int8, beam 5, VAD, `condition_on_previous_text=False`, termos do
   dicionário como `hotwords`. Modelos baixados por `recursos.py` (ATTO_CACHE); `small` embutido é o plano B.
2. `estrutura.py` — frases (pontuação/pausa), parágrafos, temas.
3. `cortes.py` — 3 camadas:
   - **Filtros duros** (`admissivel`, `e_ruido`, `tem_contagem`, `e_abertura`, `e_dependente`, `inicio_util`):
     bastidor (contagem em qualquer ordem, "gravando", "derrubando", "pronto" curto), abertura do programa nos 5 s,
     início dependente/fragmento. Tudo antes do último bastidor dos 5 primeiros minutos é ignorado.
   - **Heurística** (`_pontuar`, `nota_gancho`): gancho dos 5 s pesa 2,5x; TF-IDF; números/ênfase/perguntas; ritmo.
   - **Juiz LLM** (`juiz.py`, Qwen3-4B Q4_K_M, Apache-2.0): notas de gancho/contexto/valor/fechamento, flag de
     bastidor, frase de início e frase de **impacto** -> `com_teaser` cria o **cold open** (frase de 2–7,5 s
     repetida no começo). Sem juiz: `teaser_heuristico`.
   - Duração: 30 s a 90 s **incluindo** o gancho (`MAX_S`).
4. `ajustar_limites` — início/fim no silêncio mais próximo (análise de energia do WAV).

## Validar com um projeto real
Projetos do app ficam em `%APPDATA%/ATTO Tools/projetos/<nome>/` (transcricao.json, cortes.json, previas/).
```bash
cd apps/engine
uv run python - <<'EOF'
from pathlib import Path
from garimpo import transcricao, estrutura, cortes, juiz
p = Path(r"<pasta do projeto>")
ps, _ = transcricao.carregar(p / "transcricao.json")
ts = estrutura.temas(estrutura.paragrafos(estrutura.frases(ps)))
for c in cortes.sugerir(ts, juiz=juiz.carregar(print), log=print):
    print(round(c.ini), round(c.duracao), "|", cortes.texto_inicial(c.frases), "| gancho:", c.teaser and c.teaser.texto)
EOF
```
Confira: nenhum corte com bastidor; os 5 primeiros segundos de cada um prendem; nenhum passa de 90 s.
`ATTO_SEM_LLM=1` desliga o juiz (rápido, só heurística). Custo do juiz: ~15–25 s por finalista em CPU (até 24).

## Ao mudar regras
- Palavras de bastidor/abertura/gancho: listas no topo de `cortes.py` (casam palavras inteiras via `_contem`).
- Rubrica do juiz: `PEDIDO` em `juiz.py`; pesos em `Avaliacao.nota` (gancho 0,4).
- Sempre acrescente um teste em `tests/test_cortes_contexto.py` com o texto real que falhou.

## Referências (pesquisa 2026-11)
OpenShorts (Gemini + MediaPipe), SupoClip (notas de gancho/engajamento/valor), AI-Youtube-Shorts-Generator,
ViralCutter: todos seguem transcrição -> LLM pontua -> remove sobreposição -> corta e reenquadra. Detalhes em
`docs/pesquisa/2026-11-motion-e-cortes.md`.
