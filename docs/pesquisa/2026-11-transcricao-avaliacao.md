# Transcrição — avaliação, melhorias e pesquisa (2026-11-10, v0.7)

## 1. Prompt de avaliação (usado para revisar `transcricao.py`, `recursos.py`, `correcao/`, `pipeline.transcrever`)

> Você é engenheiro de ASR. Leia o código de transcrição do Garimpo e avalie, com nota 0–10 e evidência (arquivo:linha),
> cada critério: (1) precisão das palavras em português (WER estimado em amostra revisada); (2) pontuação, porque as
> frases e os cortes nascem dela; (3) tempo por palavra — início e fim batem com a voz?; (4) nomes próprios e termos
> do dicionário; (5) alucinação em silêncio e laços de repetição; (6) velocidade em CPU (x tempo real) e memória;
> (7) reaproveitamento: o mesmo vídeo é transcrito mais de uma vez?; (8) robustez offline. Liste os riscos em ordem
> de impacto no produto final (corte que começa/termina no meio da palavra, legenda adiantada, frase mal formada).

## 2. Resultado da avaliação (código da v0.6)
| Critério | Nota | Evidência |
|---|---|---|
| Precisão | 8 | large-v3-turbo int8 beam 5; amostra de 6 min sem erros graves |
| Pontuação | 7 | boa, mas sem prompt inicial; vírgulas oscilam |
| Tempo por palavra | 5 | tempos do Whisper puro; fim de palavra antes de pausa erra 100–300 ms (cortes 5 e 6 do teste terminavam colados na fala seguinte) |
| Nomes/termos | 7 | dicionário entra como `hotwords` |
| Alucinação | 5 | só `condition_on_previous_text=False`; nada filtra "Legendas pela comunidade Amara.org" etc. |
| Velocidade | 5 | ~1,0x tempo real (6 min de áudio em 361 s, i7 sem GPU) |
| Reaproveitamento | **1** | transcrição só na pasta do projeto, e o app cria pasta nova a cada análise → retranscreve sempre |
| Offline | 8 | `small` embutido como plano B |

## 3. Prompt de melhorias (priorizado por impacto ÷ custo)
> Com base na avaliação: (P1) cache global por conteúdo do arquivo, com chave modelo+versão+dicionário e botão
> "transcrever de novo"; (P2) refinar o início/fim das palavras na fronteira de pausas usando a energia do próprio
> WAV, sem dependências novas; (P3) filtro de alucinação por confiança (no_speech_prob, avg_logprob,
> compression_ratio), frases típicas e laços; (P4) prompt inicial em português pontuado; (P5) avaliar ganho de
> velocidade (lote, beam menor) sem perder pontuação; (P6) alinhamento forçado (wav2vec2) só se P2 não bastar.

## 4. Pesquisa (web, nov/2026)
- **WhisperX**: faster-whisper + VAD + alinhamento forçado wav2vec2 → tempos por palavra mais precisos que o
  Whisper puro (o artigo do WhisperX mostra que o tempo por palavra do Whisper sozinho é bem pior). Custo aqui:
  PyTorch + modelo wav2vec2 PT (~1,2 GB) no pacote; números ("2014", "13,60") ficam sem tempo. **Adiado**: P2
  resolve o problema prático (fronteiras de pausa) com 0 MB.
- **faster-whisper em lote** (`BatchedInferencePipeline`): medido no trecho de 6 min — 272 s contra 361 s (−25%),
  mas perde contexto entre pedaços: engoliu "para o público" e pôs ponto final no meio da frase ("Comissão do
  Trabalho."). Como pontuação é a base dos cortes, **não adotado**.
- **Silero VAD** (já embutido no faster-whisper): limiar 0,45, silêncio mínimo 500 ms, folga 200 ms.
- **Diarização (pyannote)**: modelos com acesso restrito no Hugging Face (token do usuário) — fora; a troca de
  locutor continua vindo do vídeo (rostos).
- Fontes: [WhisperX — guia](https://localaimaster.com/blog/whisperx-guide), [Fora Soft — WhisperX e tempos por palavra](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/whisperx-diarization-word-level-timestamps), [faster-whisper — guia](https://cdn.localaimaster.com/blog/faster-whisper-guide).

- **Beam 3** (mesmo trecho): 420 s, mas a pontuação desaba na 2ª metade ("nacional a gente que acompanha
  diariamente a comissão do trabalho né que é..."). **Mantido beam 5.**
- **Configuração nova** (prompt + filtro + refino): 874 palavras, texto igual ou melhor que o atual, pontuação
  preservada; o refino custa < 1 s. Medida feita em paralelo com outra análise (CPU dividida), por isso 433 s;
  o custo do Whisper em si não mudou.

## 5. O que entrou (v0.7)
P1 `cache.py` + `pipeline.transcrever(refazer=)` + app; P2 `transcricao.refinar_tempos`; P3 `_alucinado`;
P4 `PROMPT_INICIAL`. Testes: `tests/test_v07_cortes_cache.py`. Reteste do mesmo vídeo: etapa de transcrição pula
(0 s em vez de ~80 min no podcast de 80 min).
