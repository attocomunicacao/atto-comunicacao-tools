# 003 · Teste do Whisper em CPU (2026-11-06)

Máquina: Intel i7 com Iris Xe (sem NVIDIA). faster-whisper 1.2.1, `int8`, 8 threads, `language=pt`, tempo por palavra, VAD, `beam_size=1`. Amostra: 10 min de uma palestra.

| Modelo | Tempo | Velocidade |
|---|---|---|
| small | 151 s | 3,98x tempo real |
| medium | 391 s | 1,53x tempo real |

Estimativa para 3 h de áudio: small ≈ 45 min; medium ≈ 1 h 57 min.

Qualidade: o medium acertou melhor (ex.: "sindicato", "Joelma"), mas ambos erraram "SINDEPRESTEM" ("Cinti Preste", "Cinder Prestem"). Confirma a necessidade do dicionário por usuário (etapa 3/4).

Problema encontrado: PyAV 19 é incompatível com faster-whisper 1.2.1; fixado `av>=14,<17`.
Script: `apps/engine/scripts/bench_whisper.py`.
