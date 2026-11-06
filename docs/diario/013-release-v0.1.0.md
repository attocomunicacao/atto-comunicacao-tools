# 013 · Primeira release e teste do launcher na release real (2026-11-06)

Release publicada: https://github.com/attocomunicacao/atto-comunicacao-tools/releases/tag/v0.1.0 (zip de 886 MB + `manifest.json`).

## Teste do launcher contra a release real
`apps/launcher/scripts/e2e-release-real.mjs` (instala em uma pasta temporária, com os endereços oficiais):
1. O launcher consultou `releases/latest/download/manifest.json` e mostrou "Primeira instalação · ATTO Tools 0.1.0".
2. Baixou o zip do GitHub, conferiu o SHA-256 e instalou em **113 s** (`estado: atual 0.1.0`).
3. O botão **Abrir** iniciou o ATTO Tools instalado.

## Pendências
- Instalador do launcher (`.exe`) para o usuário baixar e atualização do próprio launcher.
- Workflow `release.yml` (tag -> pacote -> release) e redução do tamanho do pacote.
- Ícone, assinatura de código e teste em outro computador.
