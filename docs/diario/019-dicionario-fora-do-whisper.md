# 019 — Dicionário fora do Whisper (11/11/2026)

**Problema.** Depois de cadastrar o primeiro termo ("Izabel"), a transcrição de um podcast de 80 min ficou muito
mais lenta que o normal. Havia duas causas:

1. A chave do cache de transcrição incluía os termos do dicionário. O termo novo invalidou a transcrição guardada,
   e o vídeo foi transcrito do zero.
2. Os termos iam como `hotwords` para o faster-whisper. Medição no mesmo trecho de 3 min (large-v3-turbo, int8,
   beam 5, 12 núcleos): **131 s sem dica (1,37x o tempo real) contra 486 s com um termo (0,37x)**, e 56 trechos
   contra 38. Com a dica, o modelo refaz trechos e repete frases curtas.

**Decisão.**
- O Whisper transcreve sem dica. A grafia dos termos é corrigida depois, na etapa de dúvidas
  (`corretor.sugerir`), que já comparava com o dicionário por som e escrita.
- `cache.chave_transcricao` não usa mais os termos. Sem termos, a chave é igual à antiga com o dicionário vazio,
  então essas transcrições continuam valendo. Para transcrições gravadas com termos na chave, o pipeline também
  procura a chave antiga e copia o resultado para a nova.
