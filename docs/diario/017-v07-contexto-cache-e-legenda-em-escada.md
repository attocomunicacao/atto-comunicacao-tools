# 017 — v0.7: cache, seleção semântica, fim sem cortar fala e legenda em escada (2026-11-10)

**Problemas relatados na v0.6**: ganchos fracos, vídeo terminando no meio da fala, contexto fraco, legenda sem
conexão (espaçamento sem lógica, frases mal formadas, animação sem fluidez) e retranscrição a cada teste.

**Causas encontradas**
- O app cria uma pasta de projeto nova por análise; a transcrição só existia na pasta → retranscrevia sempre.
- `ajustar_limites` prendia o fim antes da próxima palavra mesmo quando ela vinha 0,02 s depois (outra pessoa já
  falando); e nada impedia terminar antes de um "Porém, ...".
- A quebra de linhas era gulosa (palavra a palavra) e a legenda espalhava palavras soltas numa caixa larga, com
  movimentos longos (60 px, desfoque 18 px, quique elástico).

**Decisões**: cache por conteúdo (`cache.py`); e5-small (MIT) em ONNX em vez de PyTorch; lote do faster-whisper
recusado (perde pontuação); alinhamento forçado adiado (energia do WAV resolve as fronteiras); legenda refeita a
partir das medidas da referência (docs/pesquisa/2026-11-referencias-v07.md).
