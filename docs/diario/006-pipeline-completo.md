# 006 · Pipeline completo do Garimpo, versão de motor (2026-11-06)

Comandos (em `apps/engine`):
```bash
uv run garimpo analisar <video> --pasta <projeto>      # etapas 1 a 9
uv run garimpo exportar <video> --pasta <projeto> --aprovados 1,3   # etapas 10 e 11
```

| Etapa | Módulo |
|---|---|
| 1 vídeo → WAV | `midia.extrair_wav` |
| 2 WAV → texto, com tempo em segundos e **quadros** por palavra | `transcricao` (faster-whisper small) |
| 3-5 correção e dúvidas (`duvidas.md`) | `correcao` (dicionário pessoal) |
| 6 frases → parágrafos → temas, um `.md` por tema | `estrutura`, `exportar_md` |
| 7-8 trecho mais relevante por tema, 30 s a 1min30, sem cortar frase | `cortes` |
| 9 prévia em WAV | `midia.previa_wav` |
| 10-11 corte MP4 1080x1920 (H.264 CRF 16) + legenda palavra por palavra, Lato MAIÚSCULA, destaque `#2ee6c8` | `midia.cortar_vertical`, `legenda` |

Pasta do projeto: `audio.wav`, `transcricao.json/.md`, `duvidas.md`, `frases.md`, `paragrafos.md`, `temas/tema-NN.md`, `cortes.md/json`, `previas/`, `saida/`.

## Teste real (15 min da palestra, CPU)
3 temas, 3 cortes sugeridos (49 s, 58 s...), corte exportado em 1080x1920 H.264 + AAC com legenda correta.

## Limites conhecidos
- Temas por vocabulário (sem LLM): em 15 min a divisão é grosseira. Vale testar embeddings (`nomic-embed-text`) depois.
- A "relevância" é por densidade de palavras-chave: o corte 1 caiu na abertura do evento (apresentações), que não é o melhor trecho. Precisa de um critério melhor (e do LLM só para ranquear os candidatos).
- Dúvidas só aparecem para termos já cadastrados no dicionário; a tela de aprovação virá com o app.
- Fundo desfocado + vídeo inteiro no formato vertical; o enquadramento com corte central pode ser uma opção futura.
- Lato precisa ser embarcada no instalador (licença OFL) para funcionar em outros computadores.
