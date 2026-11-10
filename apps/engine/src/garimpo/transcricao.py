"""Etapa 2: WAV -> palavras com tempo em segundos e em quadros (a linha do tempo é guardada desde o início).

Whisper large-v3-turbo (faster-whisper, int8, CPU), beam 5. Avaliação e pesquisa: docs/pesquisa/2026-11-transcricao-avaliacao.md.

v0.7:
- **prompt inicial** em português pontuado: o modelo mantém vírgulas e pontos (base das frases e dos cortes);
- **filtro de alucinação**: descarta segmentos de baixa confiança sobre silêncio, laços de repetição e as frases
  que o Whisper inventa em silêncio ("Legendas pela comunidade Amara.org", "Obrigado por assistir"...);
- **tempos refinados pela energia do áudio** (`refinar_tempos`): o Whisper erra o fim das palavras em 100-300 ms;
  o fim de cada palavra antes de uma pausa vai para onde a voz realmente acaba. É isso que impede legenda
  adiantada e corte que termina engolindo a última sílaba. (Alternativa avaliada: alinhamento forçado com
  wav2vec2 do WhisperX — exige PyTorch, +1 GB no pacote; ver a pesquisa.)
Os termos do dicionário do usuário entram como `hotwords`. Sem o modelo grande (offline), cai para o small embutido.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .modelos import Palavra

MODELO_PADRAO = "large-v3-turbo"
PROMPT_INICIAL = ("Transcrição de uma conversa em português do Brasil, com pontuação completa: vírgulas, pontos "
                  "finais e pontos de interrogação.")
ALUCINACOES = ("amara.org", "legendas pela comunidade", "obrigado por assistir", "inscreva-se no canal",
               "legendado por", "transcrição por", "ativa o sininho", "www.")
VAD = {"min_silence_duration_ms": 500, "speech_pad_ms": 200, "threshold": 0.45}


def _alucinado(seg, anteriores: list[str]) -> bool:
    t = seg.text.strip().lower()
    if not t:
        return True
    if any(a in t for a in ALUCINACOES):
        return True
    # baixa confiança sobre o que o próprio modelo acha que é silêncio
    if getattr(seg, "no_speech_prob", 0) > 0.6 and getattr(seg, "avg_logprob", 0) < -1.0:
        return True
    if getattr(seg, "compression_ratio", 0) > 2.6:   # texto muito repetitivo dentro do segmento
        return True
    # laço: o mesmo segmento 3 vezes seguidas
    return len(anteriores) >= 2 and anteriores[-1] == t and anteriores[-2] == t


def transcrever(wav: Path, fps: float, modelo: str = MODELO_PADRAO, aoProgresso=None, hotwords: list[str] | None = None,
                log=None) -> list[Palavra]:
    from faster_whisper import WhisperModel

    from . import recursos

    try:
        origem = recursos.whisper(modelo, log)
    except Exception as e:  # sem internet: usa o embutido
        if log:
            log(f"Não foi possível obter o Whisper {modelo} ({e}); usando o small embutido")
        origem = recursos.whisper("small")
    if log:
        log(f"Carregando o Whisper ({Path(origem).name}) em {os.cpu_count()} núcleos")
    m = WhisperModel(origem, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 8)
    dicas = " ".join(dict.fromkeys(hotwords or []))[:400] or None
    segs, info = m.transcribe(
        str(wav), language="pt", word_timestamps=True, beam_size=5,
        vad_filter=True, vad_parameters=VAD,
        condition_on_previous_text=False,     # evita repetições em loop em gravações longas
        initial_prompt=PROMPT_INICIAL, hotwords=dicas,
    )
    palavras: list[Palavra] = []
    total = max(getattr(info, "duration", 0.0), 1.0)
    vistos: list[str] = []
    descartados = 0
    for s in segs:
        if aoProgresso:
            aoProgresso(min(s.end / total, 1.0), s.end, total, s.text.strip())
        if _alucinado(s, vistos):
            descartados += 1
            continue
        vistos.append(s.text.strip().lower())
        for w in s.words or []:
            t = w.word.strip()
            if t:
                palavras.append(Palavra(t, w.start, w.end, round(w.start * fps), round(w.end * fps)))
    if log and descartados:
        log(f"{descartados} segmento(s) descartado(s) como alucinação/repetição do Whisper")
    try:
        from .cortes import carregar_wav
        refinar_tempos(palavras, carregar_wav(wav), fps)
        if log:
            log("Tempos das palavras refinados pela energia do áudio")
    except Exception as e:  # sem o WAV legível, ficam os tempos do Whisper
        if log:
            log(f"Refino de tempos indisponível ({str(e)[:60]})")
    return palavras


def refinar_tempos(palavras: list[Palavra], wav, fps: float) -> None:
    """Ajusta, no lugar, o fim de palavras seguidas de pausa e o início de palavras depois de pausa.

    Procura onde a energia (RMS 10 ms) cruza 15% do nível da fala vizinha: fim = último quadro com voz antes do
    silêncio; início = primeiro quadro com voz. Só move até ±0,3 s e nunca cruza a palavra vizinha."""
    import numpy as np

    from .cortes import _energia
    for i, p in enumerate(palavras):
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        ant = palavras[i - 1] if i > 0 else None
        if prox is None or prox.ini - p.fim > 0.12:          # fim antes de pausa
            lim = min(p.fim + 0.3, prox.ini - 0.02) if prox else p.fim + 0.3
            t0, e = _energia(wav, max(p.ini, p.fim - 0.3), lim)
            if len(e) > 3:
                ref = max(float(np.percentile(e, 90)), 1.0)
                voz = np.nonzero(e > 0.15 * ref)[0]
                if len(voz):
                    novo = t0 + (voz[-1] + 1) * 0.01
                    if p.ini + 0.05 < novo <= lim:
                        p.fim = round(novo, 3)
        if ant is None or p.ini - ant.fim > 0.12:              # início depois de pausa
            lim = max(p.ini - 0.3, ant.fim + 0.02) if ant else max(p.ini - 0.3, 0.0)
            t0, e = _energia(wav, lim, min(p.fim, p.ini + 0.3))
            if len(e) > 3:
                ref = max(float(np.percentile(e, 90)), 1.0)
                voz = np.nonzero(e > 0.15 * ref)[0]
                if len(voz):
                    novo = t0 + voz[0] * 0.01
                    if lim <= novo < p.fim - 0.05:
                        p.ini = round(novo, 3)
        p.quadro_ini, p.quadro_fim = round(p.ini * fps), round(p.fim * fps)




def salvar(palavras: list[Palavra], caminho: Path, fps: float) -> None:
    dados = {"fps": fps, "palavras": [vars(p) for p in palavras]}
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def carregar(caminho: Path) -> tuple[list[Palavra], float]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [Palavra(**p) for p in dados["palavras"]], dados["fps"]
