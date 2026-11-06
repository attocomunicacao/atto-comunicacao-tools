"""Etapa 2: WAV -> palavras com tempo em segundos e em quadros (a linha do tempo é guardada desde o início).

Whisper large-v3-turbo (int8, CPU), beam 5: mais lento que o small, mas acerta muito mais palavras e,
principalmente, a pontuação, que é a base para separar frases e escolher cortes que não começam no meio de
uma ideia. Os termos do dicionário do usuário entram como `hotwords` (o modelo passa a favorecer essas grafias).
Se o modelo grande não estiver disponível (sem internet na primeira vez), cai para o small embutido.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .modelos import Palavra

MODELO_PADRAO = "large-v3-turbo"


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
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
        condition_on_previous_text=False,     # evita repetições em loop em gravações longas
        hotwords=dicas,
    )
    palavras: list[Palavra] = []
    total = max(getattr(info, "duration", 0.0), 1.0)
    for s in segs:
        if aoProgresso:
            aoProgresso(min(s.end / total, 1.0), s.end, total, s.text.strip())
        for w in s.words or []:
            t = w.word.strip()
            if t:
                palavras.append(Palavra(t, w.start, w.end, round(w.start * fps), round(w.end * fps)))
    return palavras


def salvar(palavras: list[Palavra], caminho: Path, fps: float) -> None:
    dados = {"fps": fps, "palavras": [vars(p) for p in palavras]}
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def carregar(caminho: Path) -> tuple[list[Palavra], float]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [Palavra(**p) for p in dados["palavras"]], dados["fps"]
