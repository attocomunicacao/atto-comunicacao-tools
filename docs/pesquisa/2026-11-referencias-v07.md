# Referências da v0.7 — medidas quadro a quadro (2026-11-10)

Arquivos do cliente em `Downloads/videoplayback*.mp4`; folhas de contato feitas com FFmpeg (`tile`), 5–30 fps.

## videoplayback.mp4 — 7 animações de texto (14 s, 30 fps)
| s | Preset | Medida |
|---|---|---|
| 0,3–3,0 | máquina | letras surgem uma a uma, cursor "|", número "7" grande |
| 3,2–4,0 | desliza pra cima | "desliza" → "pra" → "cima": uma palavra a cada ~10 quadros; cada uma vai de ~40% a 100% em 5–6 quadros, sobe pouco (< meia letra) |
| 4,2–4,9 | desliza pra baixo | vem de cima com rastro vertical; saída: bloco todo em desfoque em 4 quadros |
| 5,0–6,0 | esquerda | 1ª palavra chega muito desfocada (6 quadros); última em serifa itálica |
| 6,0–6,8 | direita | espelho, fundo claro, serifa sem itálico |
| 6,9–7,5 | elástico | barra de luz desfocada se comprime (vertical e horizontal) até "ELÁSTICO", ~10 quadros, sem quique |
| 7,8–9,0 | entrada com desfoque | palavras em escada, cada uma do desfoque forte ao nítido |
| 9,2– | "LINK NA BIO" | glitch com cópias fantasmas |

**Composição** (o que faltava na v0.6): bloco compacto em escada, entrelinha ~0,9 (linhas quase se tocando),
cada linha deslocada um degrau, tamanho crescente (1 : 1,25 : 1,5+). O bloco deriva devagar o tempo todo.

## videoplayback (1).mp4 — flash cut (26 s, 24 fps)
0,5–1,35 s: a silhueta branca da pessoa aparece **um quadro sim, um não**, alternando plano que sai e que entra,
e termina limpo no novo plano. → `transicoes.PADRAO_ANTES/DEPOIS` quadro a quadro.

## videoplayback (2).mp4 — zoom in (30 s, 30 fps)
27,2–28,4 s: 1º quadro é um borrão a ~250%, em ~0,3 s já está perto de 140%, assenta em 100% perto de 1 s
(ease-out puxado, obturador 360°). → `ZOOM_INICIAL 2,5`, `ZOOM_DURACAO 1,0`, `tmix`; aplicado no início de todo corte.

## videoplayback (3).mp4 — narração ilustrada (21 min)
O editor divide a fala em ~15 "beats" e escolhe, para cada um, uma ilustração (pintura com texto, figura sobre
papel, espiral com número, gráfico de linha, fotos sobre papel, citação) **alternando** com o locutor + palavra
grande. O locutor some só em beats curtos. → `motion.intercalar` (locutor ≥ 60%, dominante ≤ 4,2 s, ≥ 4 s de
respiro entre dominantes) + cenas HTML/GSAP da camada ATTO Motion (contrato HyperFrames) + imagens livres.
