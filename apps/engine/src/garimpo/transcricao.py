"""Etapa 2: WAV -> palavras com tempo em segundos e em quadros (a linha do tempo é guardada desde o início)."""
from __future__ import annotations

import json
from pathlib import Path

from .modelos import Palavra


def transcrever(wav: Path, fps: float, modelo: str = "small") -> list[Palavra]:
    from faster_whisper import WhisperModel

    m = WhisperModel(modelo, device="cpu", compute_type="int8", cpu_threads=8)
    segs, _ = m.transcribe(str(wav), language="pt", word_timestamps=True, vad_filter=True, beam_size=1)
    palavras: list[Palavra] = []
    for s in segs:
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
