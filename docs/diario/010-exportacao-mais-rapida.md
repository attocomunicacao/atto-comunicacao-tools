# 010 · Exportação mais rápida (2026-11-06)

Problema: 1 corte de 61 s levava ~6 min (diário 009).

Medição em 20 s de vídeo (HEVC 1080p, legenda queimada), CPU i7:

| Variante | Tempo | Similaridade (SSIM) vs. original |
|---|---|---|
| A. antes: desfoque em tela cheia, `medium` | 71 s | - |
| B. fundo desfocado em miniatura, `medium` | 45 s | 0,995 |
| **C. B + `preset faster` (adotada)** | **26 s** | 0,994 |
| D. Intel Quick Sync (`h264_qsv`) | 19 s | 0,994, mas arquivo 14% menor |
| E. decodificação por hardware + C | 34 s | piorou (cópia de quadros) |

Escolhida a C: mesmo CRF 16 (qualidade máxima de vídeo), sem depender do hardware. Quick Sync fica como opção futura. Cerca de 11 s dos 26 s são só a decodificação do HEVC.

Resultado real (corte de 61 s): **115 s** (antes ~376 s), cerca de 3,3x mais rápido. Em `midia.cortar_vertical`.

Novos testes: `tests/test_midia.py` (vídeo sintético: extração de WAV e corte 1080x1920). 11 testes passam.
