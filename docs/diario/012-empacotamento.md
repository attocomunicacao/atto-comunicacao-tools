# 012 · Empacotamento do app (2026-11-06)

```bash
npm run package -- --versao 0.1.0
```
Gera `dist/ATTO-Tools-0.1.0-win-x64.zip` e `dist/manifest.json` (o launcher instala esse zip). Script: `scripts/package/empacotar.mjs`.

## O que vai no pacote (tudo local, sem depender do computador do usuário)
| Parte | Tamanho aprox. |
|---|---|
| App Electron (`ATTO Tools.exe`) | ~300 MB |
| Python 3.12 + dependências do `uv.lock` + código do Garimpo | 287 MB |
| FFmpeg e FFprobe (build "full") | 435 MB |
| Modelo Whisper `small` (funciona sem internet) | 464 MB |
| Lato (Regular, Bold, Black) | 0,2 MB |
| **Total** | **1,6 GB descompactado, 886 MB em zip** |

## Como o app acha as peças
Empacotado, o app usa `resources/engine/python/python.exe -m garimpo.pipeline` com `PYTHONPATH`, `PATH` (FFmpeg), `ATTO_MODELOS` (modelo) e `ATTO_FONTES` (Lato, via `fontsdir` do filtro `ass`). Em desenvolvimento continua usando `uv run`.

## Testes
- Fluxo completo do app **empacotado em ambiente limpo** (sem uv, Python, FFmpeg nem variáveis de desenvolvimento) com 6 min de palestra: transcrição em ~86 s, dúvidas, cortes com prévia e MP4 vertical gerado em ~30 s. Passou (`apps/desktop/scripts/e2e.mjs <...> <ATTO Tools.exe>`).
- O **zip real foi instalado pelo código do launcher** (download local, SHA-256, extração em 18 s) e o executável instalado abriu.

## Pendências e riscos
- **Tamanho:** 886 MB por atualização. Ideias: FFmpeg "essentials" (~100 MB), baixar o modelo à parte, atualizações incrementais (só o app, sem Python/modelo, quando não mudarem).
- **Licenças:** o FFmpeg usado é GPL v3 (ver `THIRD_PARTY_NOTICES.md`); revisar antes de distribuir fora da Atto.
- **Python:** copiado da instalação do python.org deste computador; no CI usar uma versão fixa e reproduzível.
- Ícone do app, assinatura de código (SmartScreen) e testes em outro computador ainda não foram feitos.
- O primeiro uso do GitHub Release (upload do zip) ainda não foi feito.
