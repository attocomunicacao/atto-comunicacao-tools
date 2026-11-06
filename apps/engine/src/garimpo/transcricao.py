"""Etapa 2: WAV -> palavras com tempo em segundos e em quadros (a linha do tempo é guardada desde o início)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .modelos import Palavra


def transcrever(wav: Path, fps: float, modelo: str = "small", aoProgresso=None) -> list[Palavra]:
    from faster_whisper import WhisperModel

    # Empacotado: o modelo vem junto (ATTO_MODELOS/<modelo>), funcionando sem internet.
    local = Path(os.environ.get("ATTO_MODELOS", "")) / modelo
    origem = str(local) if os.environ.get("ATTO_MODELOS") and (local / "model.bin").exists() else modelo
    m = WhisperModel(origem, device="cpu", compute_type="int8", cpu_threads=8)
    segs, info = m.transcribe(str(wav), language="pt", word_timestamps=True, vad_filter=True, beam_size=1)
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
