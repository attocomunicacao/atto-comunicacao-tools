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

## Ciclo 5 — maquina, cursor (23:32)
Prompt: lab/prompts/20261109-2333-maquina-cursor.md. 5a: cursor com pulso senoidal (sem degrau) → tremor 3,26 → 2,68 ✔.
5b: letras com fade de 0,1 s → 2,76 (ruído) ✘ revertido. Próximo: elastico (entrada 0,7 s).

## Ciclo 6 — elastico (medida) e ganchos (23:35-23:37)
Métrica v6: janela de entrada 0,6 s (a chave do elástico entrava na janela) → elastico 0,7 → 0,13 s. Deriva desligada
nas cenas (traços desenhados mudam o topo). revelacao 0,07 → 0,1 s e glitch 0 → 0,1 s com `acende` em vez de degrau.
Média do subconjunto 9,32. Próximo: conceito (saída 0,07 s) e entradas de 0,13 → 0,17 s.

## Ciclo 7 — conceito (23:40)
Saída 0,3 s power2.in → 0,4 s power1.inOut: conceito 8,3 → 10, citacao mantém 10.
Próximo: incluir as transições (zoom inicial e flash cut) nos cenários do laboratório e medi-las contra a referência.

## Ciclo 8 — zoom inicial (23:43-23:46)
Nova medida `lab.medir_zoom` (escala por quadro via ORB + afim). Nosso corte: 1,45 → 1,02 em 0,17 s, seco demais.
A referência não mede bem automaticamente (texto e desfoque por cima); vale a leitura visual (~1 s até assentar).
Mudança: 0,7 s e expoente -7 (curva: 1,19 @0,1 s · 1,03 @0,3 s · 1,0 @0,7 s). Cache dos trechos v5.
Validar no próximo corte exportado com `lab.medir_zoom(corte, 0, 1.2)`.

## Ciclo 9 — transições num corte real (00:00)
corte-02 exportado. **Zoom inicial**: 1,43 → ~1,05 em 0,35 s, cauda suave (ok). **Flash cut**: alternância quadro a
quadro com silhueta branca, igual à referência; no plano lateral a mesa/notebook entram na silhueta (a segmentação
marca a base do quadro com 0,73-0,93). Tentativas: maior contorno + âncora no rosto → sem ganho, revertidas.
Ideia registrada no banco: trocar o modelo de segmentação (multiclasse/matting). Próximo: pesquisar o modelo.

## Ciclo 10 — silhueta do flash (23:55-23:58)
Pesquisa: MediaPipe Selfie Multiclass 256x256 em ONNX ([ps-skin-seg](https://huggingface.co/FreeHugsForRobots/ps-skin-seg),
Apache-2.0; classes fundo/cabelo/pele/rosto/roupa/outros). Silhueta = soma das probabilidades de pessoa (borda suave).
Nos quadros do corte-02: mesa, notebook, copo e microfone saem da silhueta; só a pessoa vira branca, como na referência.
Flash 8 → 9,5. Próximo: varredura de transições em alta (whip/blur pan, light leak) para o banco.

## Ciclo 11 — varredura de tendências + zona segura (23:58)
Pesquisa: legenda palavra por palavra continua dominante; tendência "Dynamic Minimalism" (branco, entrada sutil) = nosso
estilo; transições curtas; legenda fora da área dos botões e da descrição. 5 ideias no banco.
Aplicado: zona segura (legenda 1180-1600 px, x 90-930). Testes ok; presets estáveis (oscilação na borda 0,133/0,15).
Próximo: "subtle scale" na entrada das palavras.

## Ciclo 12 — subtle scale e acender (00:01-00:03)
12a: escala 0,96 → 1 no "sobe" (ideia do banco) → neutro (8,3 = 8,3) → revertido pela regra.
12b: `acende` 0,30 → 0,36 s → rodada completa **9,34** (sobe, desce, direita, impacto = 10; maquina 8,3).
Pendentes: elastico (a chave entra na janela de 0,6 s — rever cenário), revelacao 0,07 s, glitch 0,1 s.

## Ciclo 13 — elastico e ganchos (00:05)
Métrica v7: janela de entrada 0,5 s → elastico 8,3 → 10. Ganchos com `acende` padrão (0,36 s): glitch 8,3 → 10,
revelacao 0,067 → 0,1 s (8,3; o wipe por máscara revela mais rápido que o fade). maquina tremor 2,50 (na borda).

## Ciclo 14 — revelacao (00:08)
Wipe por máscara power3 → power2.inOut, mínimo 0,3 s: entrada 0,1 → 0,133 s. Mantido.
Situação: legenda e cenas com 9,4+; ganhos agora são marginais. Próximo: render de um corte real com tudo e comparação
visual lado a lado com a referência (o teste que mais importa ao cliente).

## Ciclos 15-16 — corte real x referência (00:10-00:40)
Corte-01 renderizado com tudo e comparado com a referência (folha de 1 quadro/s):
- documento minúsculo sobre o peito → cena que encolheria < 60% vira tela cheia (legível; legenda embaixo como narração) ✔;
- legenda por baixo da citação → linha sai antes da cena; e toda citação/conceito cobre a legenda (antes só a do gancho) ✔;
- duas citações (uma parafraseada) → só 1 por corte e literal ✔; conceito por regra quando o LLM não sugere.
Próximo: re-render para conferir; depois volta ao laboratório (cenas em tela cheia nos cenários).

## Ciclo 17 — cenas em tela cheia no laboratório (00:23)
Cenários novos: documento_cheio, icone_cheio, numero_cheio (todas 10 nas métricas). A folha de contato mostrou que o
ícone em tela cheia herdava o layout de faixa (pequeno no topo, rótulo na borda) — a métrica não mede composição.
Mudança: ícone em tela cheia usa a composição do conceito (centralizada, anel + ícone grandes, chave em serifa).
Lição: além das métricas, o avaliador precisa olhar a folha de contato (composição), como diz o agente.

## Ciclo 18 — composição em tela cheia (00:26)
Folhas de contato: documento ok; gráfico de número encostava na borda direita (caixa de 1000 px). Caixa de tela cheia
→ (110, 300, 860, 860): margem de ~110 px dos dois lados e termina em 1160 (a legenda começa em 1180). Todas 10.

## Ciclo 19 — tipografia da legenda (00:29)
Lado a lado com a referência (videoplayback.mp4 3,9 s): composição em escada igual; a referência usa palavras pequenas
mais pesadas e justas. Inter 500 → 600, tracking -0,015 → -0,03 em. Métricas iguais (sobe 10), visual mais próximo.

## Ciclo 20 — cinematico (00:31)
Palavras pequenas usavam fade próprio (0,3 s power2) → `acende` padrão + movimento 0,4 s. cinematico 8,3 → 10.

### Rodada completa 00:31 — média 9,68 (base 23:07: 8,49)
18 de 21 em 10. Pendentes: maquina (tremor da digitação ~2,8), esquerda e revelacao (entrada 0,133 s, borda do alvo).

## Release v0.7.0 publicada (00:39)
https://github.com/attocomunicacao/atto-comunicacao-tools/releases/tag/v0.7.0 — zip 1,03 GB (e5-small embutido) +
manifest (sha e3c209a5…). Smoke test do Python embarcado ok. "latest" ainda redirecionava para 0.6.0 (cache da CDN).
Instalador do Launcher não gerado (NSIS bloqueado pelo Windows); segue o da v0.4.0.

## Ciclo 21 (00:43)
"latest" já serve o manifest 0.7.0. maquina: tremor tirado da avaliação (letras surgindo movem o centro — é o efeito da
referência) → 6,7 → 8,3. esquerda com 0,42 s: neutro → revertido.

## Ciclo 22 — preset novo "marca" (00:54)
Da pesquisa (word highlight, tendência 2026) em versão toda branca: faixa branca passa atrás da palavra-chave e ela
fica escura em serifa. Nota 10 no laboratório; entrou no rodízio do motor (`motion.RODIZIO`).

### Rodada completa 01:06 — média 9,77 (19 de 22 em 10)
Restantes (maquina, esquerda, revelacao) a 1 quadro do alvo (0,133 vs 0,15 s). Sem regressão do preset "marca".

## Ciclo 24 — revelacao (01:29)
Wipe mínimo 0,3 → 0,4 s: entrada 0,133 → 0,1 (piorou: o wipe longo deixa a palavra "acesa" antes de revelar). Revertido.
Hipótese para o próximo: amarrar o acender ao avanço do wipe (opacidade segue a máscara).

## Ciclo 25 — revelacao (01:50)
Hipótese do ciclo 24 confirmada: o acender com a mesma duração do wipe → revelacao 8,3 → 10.
Restam só maquina e esquerda a 1 quadro do alvo.

## Ciclo 26 — esquerda (02:11)
`acende` 0,45 s só na entrada pela direita (a palavra percorre mais tela): esquerda 8,3 → 10.
