# Diário do laboratório de animação

Base (23:07): média 8,49. Ponto recorrente: entrada das palavras rápida demais (0,03-0,1 s vs 0,17-0,35 s na referência).

## Ciclo 1 — maquina (23:10)
Prompt: lab/prompts/20261109-2315-maquina.md. Mudança: digitação ≤ 55% da palavra, cursor fixo e pisca 1 Hz depois.
maquina 6,7 → 6,7 (tremor 3,26 → 2,74; entrada 0,53 → 0,50). cinematico 8,3 → 6,7 SEM mudança de código: a deriva
oscila perto do limite (2,6 vs 3 px) — ruído da métrica. Decisão: manter. Próximo: entrada curta das palavras (sobe/desce/direita/deslocamento).

## Ciclo 2 — entrada das palavras (23:13-23:16)
Prompt: lab/prompts/20261109-2316-entradas.md. Pesquisa: ~400 ms ease-out, opacidade sem "estalo"
([motion-guide](https://motion-guide.pages.dev/entry/kinetic-headline-reveal), [Framer](https://framerwebsites.com/blog/framer-text-animations)).
Mudança: opacidade em tween próprio (`acende`, 0,26 s power1.out) + movimento expo 0,42 s.
A métrica binária (área > limiar) não enxergava a mudança: com 30% de opacidade o texto já "contava".
**Métrica v2**: intensidade (não área), palavras de teste espaçadas 0,8 s, entrada = até 90% do nível da 1ª palavra,
saída = idem no fim. Nova base: média 7,32 (entradas ~0,5 s; alvo ≤ 0,45). Decisão: manter.

## Ciclo 3 — métrica v4 + acender 0,3 s (23:19-23:24)
Folha a 30 fps de "sobe" mostrou a palavra indo de cinza a branco em ~5 quadros (igual à referência), mas a métrica
dava 0,5 s: o ruído de compressão fazia o "início" cair no quadro 0. Métrica v4 desconta esse ruído.
Com v4: entradas 0,1 s (referência 0,17-0,2) → `acende` 0,2 → 0,3 s → entradas 0,13 s. Média 7,12 → **8,33**.
Próximo: deriva do bloco 1-3 px (referência 5-15 px) e "elastico" com entrada 0,7 s.

## Ciclo 4 — deriva do bloco (23:27-23:28)
Mudança: `viver` deriva y −10 → −18 px e escala 2,2% → 3%, curva sine.out (desacelera, nunca para de vez).
A deriva medida antes usava só o trecho com o bloco completo (curto); métrica v5 mede o topo do 1º elemento por 1 s.
Média 8,33 → **9,16**. Restam: elastico (entrada 0,7 s), maquina (tremor 3,3), revelacao/glitch (entrada < 0,1 s),
conceito (saída 0,07 s).
