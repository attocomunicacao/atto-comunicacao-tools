# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões seguem `x.y.z`.

## [0.1.0] - 2026-11-06

Primeira versão de testes.

### Adicionado
- **Garimpo**: transcrição local (faster-whisper `small`), dicionário pessoal com correção por busca fonética, separação em frases, parágrafos e temas (`.md`), sugestão de cortes de 30 s a 1min30 sem cortar frases, prévia em áudio e geração de MP4 vertical 1080×1920 com legenda palavra por palavra (Lato maiúscula).
- **ATTO Tools** (janela do app) com identidade visual da ATTO: vídeo, transcrição, dúvidas, cortes e exportação, além de "Meu dicionário".
- **Launcher**: instala e atualiza lado a lado, confere o SHA-256 e permite voltar à versão anterior.
- Empacotamento (Electron + Python + FFmpeg + modelo + fontes) e `manifest.json` da release.
- Site de apresentação e documentação do desenvolvimento em `docs/diario`.

### Conhecido
- Pacote de cerca de 886 MB; o app não é assinado digitalmente (SmartScreen avisa); a escolha automática dos melhores trechos ainda pode trazer conversa de abertura.
