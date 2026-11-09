---
name: garimpo-motion
description: Use ao mexer na edição dos cortes do Garimpo — legenda animada, ilustrações (números, comparações, ícones, frases-chave), zooms de ênfase, transições, cold open, logo final ou áudio. Explica a camada ATTO Motion (HTML + GSAP renderizada quadro a quadro pelo Electron), o plano gerado pelo motor Python e como testar um render.
---

# ATTO Motion (edição dinâmica dos cortes)

## Arquitetura (quem faz o quê)
1. **Plano** — `apps/engine/src/garimpo/motion.py` (`planejar`): palavras com ênfase, cenas ilustrativas
   (regras + LLM Qwen3-4B), instantes de zoom e transições. Tempos em segundos do corte montado.
2. **Vídeo-base** — `apps/engine/src/garimpo/midia.py`:
   - `trecho_vertical`: reenquadra (rosto / tela dividida, `enquadramento.py`) e aplica zooms com `zoompan` sobre
     supersampling 2x (sem tremor);
   - `montar`: concatena gancho + corpo, masteriza o áudio (`MASTER_AUDIO`: highpass, compressor, loudnorm -14 LUFS)
     e acrescenta o cartão da logo.
3. **Camada de motion** — `apps/desktop/src/renderer/src/motion/` (`main.ts`, `motion.css`, `tipos.ts`):
   página `motion.html` com UMA timeline GSAP pausada. Contrato (igual ao HyperFrames): nada de relógio, timers ou
   aleatório; todo quadro é função do tempo.
4. **Render** — `apps/desktop/src/main/renderMotion.ts`: `ATTO Tools.exe --render-motion job.json` abre a página
   offscreen (1080x1920, transparente, escala 1), faz `__seek(t)` + `capturePage` por quadro e manda BGRA para o
   FFmpeg, que sobrepõe ao vídeo-base. O motor chama via `ATTO_MOTION_CMD` (definido pelo app) e lê `PCT n`.

Sem `ATTO_MOTION_CMD` (linha de comando pura), o motor cai para a legenda ASS (`legenda.py`) queimada no base.

## Regras de estilo (pedido do cliente)
- Legenda: uma palavra por vez, MAIÚSCULA, branca, Lato 900, 64 px, centro em y=1400, glow branco, sem traçado.
- Entrada: y -100 -> 0, opacidade 0 -> 1, blur 14 -> 0, escala 0.9 -> 1, `expo.out`, até 0,55 s (encurta se a
  palavra for curta — nunca termina depois da saída). Respira (y -6) parada. Saída: +18 px, blur 9, 0,18 s `power2.in`.
- Ilustrações na faixa inferior (top 1500 px), cartão escuro translúcido, tudo branco, uma família (Lato).
- Nada de cores além de branco/preto translúcido.

## Adicionar um tipo de ilustração
1. `tipos.ts`: novo valor em `Cena['tipo']` e campos.
2. `main.ts`: `cartao()` (markup) e `cenas()` (tweens na timeline `t`, sempre em tempos absolutos `c.ini + x`).
3. `motion.css`: estilo.
4. `motion.py`: gerar a cena (regras e/ou `PEDIDO_LLM`), e prioridade em `_espacar`.
5. Teste em `apps/engine/tests/test_motion.py` e um render (abaixo).

## Testar um render
```bash
cd apps/desktop && npm run build
npx electron . --render-motion caminho/job.json   # job: base, saida, fps, duracao, largura, altura, palavras, cenas
```
Depurar um quadro: no job, `"depurar": "q.png", "depurarEm": 1.0` salva o PNG (transparente) daquele instante.
Ponta a ponta (como o app): defina `ATTO_MOTION_CMD='["<electron.exe>", "<apps/desktop>", "--render-motion"]'` e
rode `uv run garimpo exportar <video> --pasta <projeto> --aprovados N`. Confira quadros com
`ffmpeg -vf "select=...,tile=8x1"` e o loudness com `-af ebur128` (alvo -14 LUFS).

## Armadilhas já encontradas
- BrowserWindow offscreen é limitada à altura da tela: usar `enableLargerThanScreen` + `setContentSize`.
- Tween de entrada que termina depois da saída "ressuscita" a palavra: a entrada é encurtada.
- O Qwen3 devolve números como texto ("3. [9.0s] ...", "8/10", 75000000 com sufixo "mi"): use `inteiro_em`,
  `_num` e `_escala`.
- Velocidade: ~14 quadros/s no render da camada; zoompan 2x ~1,2x tempo real.
