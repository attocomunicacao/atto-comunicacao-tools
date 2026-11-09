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

## Regras de estilo (pedido do cliente, referência "minimal premium" — youtu.be/g9xoKm5DEeU)
- Tudo branco. Duas famílias: Inter (texto, minúsculas) e Playfair Display itálico (palavra-chave). Sem cartões.
- Legenda: linhas de até 5 palavras (`motion.grupos_legenda`); a palavra-chave fica grande no centro (serifa
  itálica; números em Inter 800), as demais pequenas acima/abaixo, surgindo no tempo da fala. Chave: blur 18→0,
  y −60→0, letter-spacing 0,08em→0, 0,85 s `expo.out`. Linha sai inteira em desfoque.
- Cenas flutuando sobre o vídeo com vinheta escura suave: `destaque` = linha + texto; `numero`/`comparacao` =
  gráfico (grade com brilho, curva e bolinha); `icone` = ícone de traço + órbita; `citacao` = tela escurecida com
  textura, aspas e frase escrita (usada no cold open, cobre a legenda); `pintura` = b-roll em tela cheia (Met
  Museum, domínio público, `recursos.pintura`) com textura de papel, bordas escuras e "camera slide".
- Transição do cold open: faixa de luz diagonal + flash.
- Iterar rápido: `ATTO_MANTER_TMP=1` mantém os trechos reenquadrados em cache; só a camada de motion é refeita.

## Motores (v0.6) — leia `docs/motor-edicao.md`
- **Presets de legenda**: `motion.escolher_presets` (contexto → preset) e `motion/legendas.ts` (8 presets de linha +
  3 de gancho, lidos das referências em `docs/pesquisa/2026-11-referencias-edicao.md`).
- **Transições**: `transicoes.py` — flash cut (silhueta branca, MediaPipe) e zoom 230%→100% com desfoque de movimento;
  `enquadramento.estilos_troca` alterna nas trocas de locutor; gancho → corpo sempre em flash cut.
- **Mapa de espaço**: `espaco.py` — nada sobre o rosto; cenas encaixadas (`encaixar` em `main.ts`).
- **Cena documento** (estilo Vox) para lei/decisão/projeto: `motion.documentos_por_regras` + `cenaDocumento`.
- Revisão: agente `revisor-de-edicao` (folha de contato + plano).

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
