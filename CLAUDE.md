# ATTO Tools — guia para agentes

Monorepo da suíte desktop da Atto Comunicação (Windows). Textos, código e commits em **português**.

- `apps/engine` — motor Python (uv): transcrição, seleção de cortes, enquadramento, edição. `uv run pytest -q`.
- `apps/desktop` — app Electron + React (Garimpo) e a camada **ATTO Motion** (`src/renderer/src/motion`), renderizada
  pelo próprio executável em `--render-motion`. `npx tsc --noEmit -p . && npm run build`.
- `apps/launcher` — instala/atualiza o app pelas releases do GitHub.
- `scripts/package` — empacotador (Python embarcado, FFmpeg, fontes, modelo small).
- `docs/diario` — uma entrada por decisão/marco; `docs/motion.md` — especificação do motion.

Skills do projeto (`.claude/skills`): `garimpo-motion` (edição/animação), `garimpo-legenda` (legenda: linhas,
palavra-chave, espaço), `garimpo-cortes` (seleção e transcrição), `atto-release` (publicar versão). Agente
`legendista` (`.claude/agents`) revisa o plano de legenda de um corte. Leia a skill antes de mexer na área.

Combinado com o cliente: cada pacote de atualizações é implementado, testado, commitado na `main` e publicado como
release (app + Launcher) — ver `atto-release`.

Estilo pedido (ref. youtu.be/g9xoKm5DEeU, "minimal premium"): tudo branco; legenda em linhas de até 5 palavras com
a palavra de sentido em Playfair itálico e as demais pequenas em Inter; ilustrações sem cartão; imagens livres com
efeito 3D; som sutil. Cortes de até 90 s com gancho forte nos 5 primeiros segundos; nada de bastidor de gravação.
