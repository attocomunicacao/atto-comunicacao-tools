# Motores de edição do Garimpo (v0.7)

Fluxo de `pipeline.exportar` para cada corte:

```
plano (motion.planejar)
  ├─ legenda: grupos_legenda (regras) → chaves_por_llm (palavra de sentido) → sem_chave → escolher_presets
  ├─ cenas: regras (número, comparação, ícone, documento) + LLM (cenas, título, imagens) → _espacar → com_imagens (3D)
  └─ zooms de ênfase, transições (cold open)
trechos (midia.trecho_vertical)       reenquadra (rosto / tela dividida) + zoom de troca de locutor + punch-ins
montagem (pipeline.transicoes_da_montagem + midia.montar)
  └─ flash cuts encaixados (gancho → corpo, trocas de locutor), áudio −14 LUFS, sons, logo final
mapa de espaço (espaco.mapear + espaco.aplicar)   rostos no vídeo montado → caixa livre de cada legenda/cena
camada ATTO Motion (Electron --render-motion)     legendas.ts (presets) + main.ts (cenas) + imagem3d.ts (WebGL)
```

## Motor de presets da legenda (`motion.escolher_presets` + `motion/legendas.ts`)
| Contexto | Preset |
|---|---|
| até o fim do gancho (cold open ou 4,5 s) | **impacto** → **revelação** → **glitch** (os 3 de gancho, em ordem) |
| linha com "?" | **máquina** de escrever |
| linha com número | **elástico** |
| começa com contraste ("mas", "não", "porém"...) | **esquerda** / **direita** (alternando) |
| palavra-chave forte (peso ≥ 2,5) | **sobe** |
| demais | rodízio **cinemático, deslocamento, sobe, cinemático, desce, deslocamento**, nunca igual à anterior |

## v0.7 — mudanças
- **Transições**: todo corte abre com **zoom in** (250% → 100% em 1 s, `filtro(zoom_inicio=True)`); **toda troca
  de locutor é flash cut**, agora com silhueta quadro a quadro (`PADRAO_ANTES/DEPOIS`).
- **Legenda**: bloco em escada e movimento curto (`legendas.ts`); quebra ótima das linhas (`motion.segmentar`).
- **Intercalação** (`motion.intercalar`): cada cena é `parcial` (na caixa livre, locutor visível) ou `dominante`
  (imagem 3D, pintura, citação); locutor visível ≥ 60%, dominante ≤ 4,2 s, ≥ 4 s de locutor limpo entre elas.

## Motor de transições (`transicoes.py`)
- **Flash cut**: 0,4 s antes + 0,4 s depois do corte, blocos de 2 quadros no padrão
  `A, A·branco, A, B·branco, A, A·branco | B, B·branco, A, B·branco, B, B` (silhueta por MediaPipe Selfie
  Segmentation). Usado no gancho → corpo e nas trocas de locutor ímpares. Duração e áudio intactos.
- **Zoom**: o plano que entra começa a 230% e assenta em 100% em 0,5 s (`1+(2,3−1)·2^(−10p)·(1−p)`), com `tmix` de
  4 quadros (desfoque de movimento). Trocas de locutor pares.
- Regra: `enquadramento.estilos_troca` alterna zoom / flash a cada troca.

## Mapa de espaço (`espaco.py`)
- Rostos detectados no vídeo montado (YuNet, 4 quadros/s, 1/3 da resolução: ~8 s por corte).
- Faixas livres de largura total entre os rostos (com margem e queixo) + laterais de um rosto único.
- Legenda: prefere 1270–1760 px; se o rosto ocupa a base (tela dividida), vai para a maior faixa livre.
- Cenas: faixas em 110–1250 px ou laterais; a cena é **reduzida para caber** (`encaixar`, sem distorcer).
- Cena e legenda na mesma faixa ao mesmo tempo: a cena fica com a metade de cima.

## Cenas
`destaque` (linha + texto), `numero`/`comparacao` (gráfico), `icone` (traço + órbita), `documento` (estilo Vox),
`citacao` (tela cheia, cobre a legenda), `imagem` (foto livre com 3D), `pintura` (reserva). Espaçamento mínimo 5,5 s,
até 6 por corte, no máximo 3 ícones.

## Revisão do código (2026-11-09) — achados e correções
| Achado | Correção |
|---|---|
| `trecho_citacao` podia entrar em laço infinito (índice oscilando ±1) | laço limitado, só avança |
| Qwen3-4B com gramática JSON respondia `{}` no pedido longo de cenas | pedido sem gramática + extração tolerante |
| LLM de 4B não segmenta legenda (linhas de 1–2 palavras) | quebra por regras; LLM só escolhe a palavra-chave |
| Buscas genéricas traziam imagem fora de contexto/sensível | categorias curadas do Commons, relevância no título, bloqueio de temas |
| Ilustrações e textos podiam cobrir o rosto | mapa de espaço + encaixe |
| Transição única (dissolução) entre locutores | motor de transições (zoom/flash) |
| Animação de legenda única | 8 presets + 3 de gancho |
| Iteração lenta | cache dos trechos (`ATTO_MANTER_TMP=1`, chave inclui versão do motor) |

Custos medidos (i7, sem GPU): flash cut ~6 s cada; mapa de espaço ~8 s/corte; profundidade ~13 s/imagem;
render da camada ~14 quadros/s; LLM ~35 s (chaves) + ~60 s (cenas) por corte.
