# Ciclo 28 — maquina (2026-11-10)

Alvo: `maquina` (legenda). Nota oscila 8,3 ↔ 10 com o mesmo código: entrada_s = 0,133 s (alvo 0,15-0,45) —
a 1ª palavra ("qual", 4 letras) termina de digitar no limite, e cada letra "estala" em 0,03 s (1 quadro).

Mudança (UMA): em `apps/desktop/src/renderer/src/motion/legendas.ts`, função `maquina`, o tween de cada letra
passa de `duration: 0.03` (sem curva) para um fade curto de ~0,08 s com `ease: 'power1.out'` (2-3 quadros,
como digitação profissional: a letra acende em vez de estalar). Não mexer no ritmo das letras, no cursor nem no
resto.

Sucesso: maquina entrada_s ≥ 0,15 de forma estável (nota 10), salto não piora; vizinhos cinematico e sobe = 10.
