# Motion dos cortes (especificação)

Tela 1080x1920, fps do vídeo de origem. Tudo branco, uma família (Lato), glow branco.

| Elemento | Posição | Entrada | Parada | Saída |
|---|---|---|---|---|
| Palavra da legenda (64 px, 900, maiúscula) | centro, y=1400 | y −100→0, opacidade 0→1, blur 14→0, escala 0,9→1; `expo.out`, até 0,55 s | deriva y −6 (`sine.inOut`) | +18 px, blur 9, opacidade 0; 0,18 s `power2.in`, cruza com a próxima |
| Palavra de ênfase (número, "nunca", "lei"...) | idem | escala 0,75→1,14, glow mais forte | idem | idem |
| Cartão ilustrativo | faixa inferior (top 1500, 90 px de margem) | y +70→0, escala 0,94→1, blur 16→0; 0,7 s `expo.out` | flutua y −10 | y −40, blur 14; 0,4 s `power2.in` |
| Número | no cartão, 132 px | conta de 0 ao valor (`power3.out`, ≤1,4 s), `back.out(2)` | — | com o cartão |
| Comparação | no cartão, 96 px | antes desliza; seta desenha o traço; depois "pula" (`back.out(2.2)`) | — | com o cartão |
| Ícone (Lucide) | no cartão, 150 px | traço desenhado (dashoffset 1→0, stagger 0,08) + `elastic.out` | — | com o cartão |
| Frase-chave / título-gancho | no cartão, 74 px | palavras em stagger 0,07 com blur | — | com o cartão |
| Flash (fim do cold open) | tela toda | branco 0→0,85 em 0,08 s | — | 0,3 s |
| Zoom de ênfase (no vídeo) | centro, y 42% | 1→1,09 smoothstep 0,55 s | 1,8 s | 0,8 s |
| Logo final | centro | escurece 62%, logo sobe 70 px com fade (0,6–0,8 s) | 2,2 s no total | — |

Espaçamento: no máximo 6 ilustrações por corte, 5,5 s entre inícios; zooms a cada ≥ 6 s.
Áudio: highpass 75 Hz, compressor 3:1, loudnorm −14 LUFS / −1,5 dBTP.
