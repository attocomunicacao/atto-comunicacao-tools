"""Design de som dos cortes: efeitos sutis presos às animações (bem abaixo da voz).

- whoosh: transição do cold open e entrada de imagem/citação em tela cheia;
- clique: entrada de linha + texto e de ícone;
- impacto: número e comparação (gráfico).

Os arquivos vêm da pasta de sons do usuário (ATTO_SONS, preenchida pelo app com os efeitos que ele anexar, ex.:
baixados da Epidemic Sound com a conta dele: `whoosh.*`, `clique.*`, `impacto.*`). Sem arquivo, o FFmpeg sintetiza
um efeito padrão discreto (sem direitos de terceiros).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import recursos

TIPOS = ("whoosh", "clique", "impacto")
VOLUME_DB = {"whoosh": -17.0, "clique": -22.0, "impacto": -16.0}  # relativo a 0 dBFS, depois da voz a -14 LUFS

SINTESE = {
    "whoosh": ("anoisesrc=d=0.75:c=pink:a=0.6:r=48000,highpass=f=350,lowpass=f=5200,"
               "afade=t=in:d=0.42:curve=exp,afade=t=out:st=0.42:d=0.33:curve=exp,"
               "aecho=0.6:0.4:40:0.3,pan=stereo|c0=c0|c1=c0"),
    "clique": ("sine=f=2100:d=0.06:r=48000,afade=t=out:d=0.06:curve=exp,highpass=f=900,"
               "pan=stereo|c0=c0|c1=c0"),
    "impacto": ("sine=f=58:d=0.6:r=48000,afade=t=out:d=0.6:curve=exp,volume=2.5,"
                "pan=stereo|c0=c0|c1=c0"),
}


def arquivo(tipo: str) -> Path | None:
    """Efeito do usuário (se anexado no app) ou o sintetizado padrão (gerado uma vez no cache)."""
    pasta = os.environ.get("ATTO_SONS")
    if pasta and Path(pasta).exists():
        for f in Path(pasta).iterdir():
            if f.stem.lower() == tipo and f.suffix.lower() in (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"):
                return f
    destino = recursos.pasta_cache() / "sons" / f"{tipo}.wav"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", SINTESE[tipo], str(destino)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
    return destino


def eventos(cenas: list[dict], transicoes: list[float]) -> list[tuple[float, str]]:
    """Quando e qual som: um por animação relevante, sem empilhar (mín. 0,6 s entre dois)."""
    ev: list[tuple[float, str]] = [(max(t - 0.35, 0), "whoosh") for t in transicoes]
    for c in cenas:
        tipo = c.get("tipo")
        if tipo in ("imagem", "pintura", "citacao"):
            ev.append((max(c["ini"] - 0.1, 0), "whoosh"))
        elif tipo in ("numero", "comparacao"):
            ev.append((c["ini"] + 0.35, "impacto"))
        elif tipo in ("icone", "destaque"):
            ev.append((c["ini"] + 0.2, "clique"))
    ev.sort()
    saida: list[tuple[float, str]] = []
    for t, tipo in ev:
        if not saida or t - saida[-1][0] >= 0.6:
            saida.append((round(t, 3), tipo))
    return saida


def faixa(ev: list[tuple[float, str]]) -> list[tuple[float, Path, float]]:
    """(instante, arquivo, volume em dB) prontos para a mixagem; ignora tipos sem arquivo."""
    saida = []
    for t, tipo in ev:
        f = arquivo(tipo)
        if f:
            saida.append((t, f, VOLUME_DB[tipo]))
    return saida
