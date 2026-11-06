# 014 · Site e README comerciais (2026-11-06)

- **README** no padrão do soul-cars-app: banner, links rápidos, selos, o que é, telas, instalação, princípios, arquitetura, desenvolvimento e licença.
- **Site** em `website/index.html` (HTML único, identidade ATTO, responsivo, sem rolagem horizontal em 375 px), publicado pelo workflow `.github/workflows/pages.yml` no GitHub Pages: https://attocomunicacao.github.io/atto-comunicacao-tools/
- **Capturas com dados fictícios**: `npm run capturas` abre o app com uma ponte simulada (`apps/desktop/scripts/demo/mock-atto.js`) e salva as telas. Substitui as capturas anteriores, que mostravam trechos de uma palestra real de cliente.
- `CHANGELOG.md` com a versão 0.1.0.

## Atenção
As capturas antigas (`02-duvidas.png` com texto de uma palestra real) continuam no histórico do git (commit `fb9620d`), embora não estejam mais nos arquivos atuais. Para removê-las de vez é preciso reescrever o histórico, o que exige decisão explícita.
