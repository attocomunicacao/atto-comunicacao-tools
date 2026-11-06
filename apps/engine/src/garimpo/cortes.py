"""Etapas 7-8: escolhe o trecho mais relevante de cada tema (30 s a 1min30, sem cortar frases)."""
from __future__ import annotations

from collections import Counter

from .estrutura import tokens
from .modelos import Corte, Frase, Tema

MIN_S = 30.0
MAX_S = 90.0


def _pontuar(fs: list[Frase], chaves: Counter) -> float:
    palavras = sum(len(f.palavras) for f in fs)
    dur = fs[-1].fim - fs[0].ini
    if palavras == 0 or dur <= 0:
        return 0.0
    densidade = sum(chaves[t] for f in fs for t in tokens(f.texto)) / palavras
    ritmo = 1.0 - abs(dur - 60.0) / 60.0  # prefere perto de ~60 s
    return densidade * (0.6 + 0.4 * max(ritmo, 0.0))


def melhor_corte(tema: Tema) -> Corte | None:
    fs = tema.frases
    chaves = Counter(t for f in fs for t in tokens(f.texto))
    melhor: Corte | None = None
    for i in range(len(fs)):
        for j in range(i, len(fs)):
            dur = fs[j].fim - fs[i].ini
            if dur > MAX_S:
                break
            if dur >= MIN_S:
                c = Corte(tema.titulo, fs[i:j + 1], _pontuar(fs[i:j + 1], chaves))
                if melhor is None or c.pontuacao > melhor.pontuacao:
                    melhor = c
    return melhor


def sugerir(temas: list[Tema]) -> list[Corte]:
    """Um corte por tema que comporte pelo menos 30 s, em ordem cronológica."""
    cortes = [c for t in temas if (c := melhor_corte(t))]
    return sorted(cortes, key=lambda c: c.ini)
