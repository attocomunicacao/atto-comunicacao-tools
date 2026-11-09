---
name: atto-release
description: Use para publicar uma nova versão do ATTO Tools no GitHub (zip do app, manifest para o Launcher e instalador .exe do Launcher). Cobre versão, empacotamento, limites do GitHub e conferência do manifest.
---

# Release do ATTO Tools

O usuário quer que cada pacote de atualizações chegue ao GitHub e ao Launcher. Fluxo:

1. Testes: `cd apps/engine && uv run pytest -q`; `cd apps/desktop && npx tsc --noEmit -p . && npm run build`;
   `npm test` na raiz (Launcher).
2. CHANGELOG: nova seção `## [x.y.z] - AAAA-MM-DD` no topo; README se mudou requisito/tamanho.
3. Versão do Launcher: `apps/launcher/package.json` -> `"version": "x.y.z"` (nome do instalador sai daqui).
4. Commit e push na `main` (assinatura de coautoria da sessão).
5. Pacote do app (a versão NÃO vem do package.json do desktop, que é 0.0.0):
   `node scripts/package/empacotar.mjs --versao x.y.z` -> `dist/ATTO-Tools-x.y.z-win-x64.zip` + `dist/manifest.json`.
6. Instalador do Launcher: `npm run instalador` -> `dist/launcher/ATTO-Tools-Setup-x.y.z.exe`.
7. Release: `gh release create vx.y.z <zip> dist/manifest.json <setup.exe> --title "ATTO Tools x.y.z" --notes "..." --latest`.
8. Conferir: `curl -sL https://github.com/attocomunicacao/atto-comunicacao-tools/releases/latest/download/manifest.json`
   mostra a versão nova e o `sha256` bate com `sha256sum` do zip.

## Armadilhas
- Limite de 2 GB por arquivo de release: modelos grandes (Whisper turbo, Qwen3-4B) NÃO vão no zip; são baixados
  na primeira análise (`garimpo/recursos.py`, pasta `%APPDATA%/ATTO Tools/modelos`).
- Upload grande pode falhar com HTTP 500 e deixar a release como **Draft**: `gh release upload vx.y.z <arquivos> --clobber`
  e depois `gh release edit vx.y.z --draft=false --latest`.
- `llama-cpp-python` vem do índice de binários CPU (já configurado no empacotador).
- Rodar o empacotador em segundo plano (leva minutos) e não iniciar dois ao mesmo tempo.
- Smoke test do pacote: `dist/ATTO Tools-win32-x64/resources/engine/python/python.exe -s -c "import llama_cpp, cv2, faster_whisper; from garimpo import juiz, motion"`
  com `PYTHONPATH=<resources>/engine/site-packages`.
