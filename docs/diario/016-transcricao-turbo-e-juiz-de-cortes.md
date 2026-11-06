# 016 · Transcrição large-v3-turbo, seleção de cortes em 3 camadas e legenda com motion (2026-11-06)

## Problema
No podcast real de 80 min, o corte 1 começava em "Pronto. Derrubando em 5, 4, 3, 2... Olá, estamos aqui inaugurando...".
A lista de ruídos só conhecia contagem crescente ("1, 2, 3") e não conhecia "derrubando"; a abertura do programa tinha só
penalidade leve. Os 5 primeiros segundos (o gancho) eram justamente bastidor.

## Como as ferramentas de corte automático escolhem trechos (pesquisa)
- SupoClip (código aberto): LLM escolhe segmentos e dá notas de gancho, engajamento, valor e compartilhamento.
- Rankers descritos publicamente: notas por critério (gancho, pico emocional, opinião forte, frase citável, valor prático) e
  **remoção de sobreposições** antes de pegar os N melhores.
- OpusClip e similares não publicam o método; descrevem gancho, argumento autocontido, picos emocionais e frases citáveis.
Fontes: github.com/FujiwaraChoki/supoclip, moclaw.ai/blog/free-ai-shorts-generator, autoclip.dev/blog/best-ai-clip-finder-tools.

## Decisão: 3 camadas
1. **Filtros duros**: contagem em qualquer ordem (dígitos ou por extenso), bastidor ("gravando", "derrubando", "pronto"
   em frase curta…), abertura do programa nos 5 primeiros segundos, frase dependente ou fragmento no início. Tudo antes do
   último sinal de bastidor dos 5 primeiros minutos é ignorado (no podcast: 194 s).
2. **Heurística** em todas as janelas, com o gancho (5 s iniciais) pesando 2,5x.
3. **Juiz LLM local** nos finalistas (até 24): Qwen3-4B Q4_K_M via llama.cpp, rubrica gancho/contexto/valor/fechamento,
   flag de bastidor e sugestão de frase de início. Qwen2.5-3B foi descartado por licença (Qwen Research, não comercial).
   Custo medido: ~15-20 s por finalista em CPU (i7, Iris Xe).

## Transcrição
Whisper large-v3-turbo, int8, beam 5, VAD, `condition_on_previous_text=False`, termos do dicionário como `hotwords`.
Amostra de 2 min do podcast: beam 1 = 58 s; beam 5 = 73 s (0,6x tempo real), com pontuação muito melhor (base da
separação de frases). O `small` segue embutido como plano B offline.

## Distribuição
Turbo (1,6 GB) e Qwen3-4B (2,5 GB) não cabem no zip (limite de 2 GB por arquivo de release): são baixados na primeira
vez para `%APPDATA%/ATTO Tools/modelos`, com progresso na tela de carregamento.

## Legenda
Motion lido quadro a quadro do vídeo de referência: palavra entra desfocada, assenta com easing exponencial, e sai
desfocando e descendo enquanto a próxima entra. Desenhado a 60 eventos/s.
