"""Etapa 6: palavras -> frases -> parágrafos -> temas (sem LLM: pausas e vocabulário)."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from .modelos import Frase, Palavra, Paragrafo, Tema

FIM_FRASE = (".", "?", "!", "…")
PAUSA_FRASE = 0.9
PAUSA_PARAGRAFO = 1.6
MAX_PALAVRAS_PARAGRAFO = 90

STOP = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sobre entre e ou mas que se
como mais menos muito muita muitos muitas ja nao sim ser estar ter haver foi era eh sao esta estao tem tinha vai vou
isso isto esse essa esses essas aquele aquela eu voce voces ele ela eles elas nos gente me te lhe meu minha seu sua
nosso nossa aqui ali la entao ai assim tambem so ate quando onde porque pra pro pelo pela depois antes agora bem
tipo coisa coisas fazer faz fez pode podem""".split())


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def tokens(texto: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", _norm(texto)) if w not in STOP]


def frases(palavras: list[Palavra]) -> list[Frase]:
    saida: list[Frase] = []
    atual: list[Palavra] = []
    for i, p in enumerate(palavras):
        atual.append(p)
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        if prox is None or p.texto.endswith(FIM_FRASE) or prox.ini - p.fim >= PAUSA_FRASE:
            saida.append(Frase(atual))
            atual = []
    return saida


def paragrafos(fs: list[Frase]) -> list[Paragrafo]:
    saida: list[Paragrafo] = []
    atual: list[Frase] = []
    n = 0
    for i, f in enumerate(fs):
        atual.append(f)
        n += len(f.palavras)
        prox = fs[i + 1] if i + 1 < len(fs) else None
        if prox is None or prox.ini - f.fim >= PAUSA_PARAGRAFO or n >= MAX_PALAVRAS_PARAGRAFO:
            saida.append(Paragrafo(atual))
            atual, n = [], 0
    return saida


def _cos(a: Counter, b: Counter) -> float:
    num = sum(a[k] * b[k] for k in a if k in b)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def temas(ps: list[Paragrafo], janela: int = 3, min_paragrafos: int = 4) -> list[Tema]:
    """Fronteira de tema onde o vocabulário dos parágrafos vizinhos mais muda (estilo TextTiling)."""
    if not ps:
        return []
    bag = [Counter(tokens(p.texto)) for p in ps]
    sim = []
    for i in range(1, len(ps)):
        esq, dir_ = Counter(), Counter()
        for b in bag[max(0, i - janela):i]:
            esq.update(b)
        for b in bag[i:i + janela]:
            dir_.update(b)
        sim.append(_cos(esq, dir_))
    if sim:
        media = sum(sim) / len(sim)
        desvio = math.sqrt(sum((s - media) ** 2 for s in sim) / len(sim))
        corte = media - 0.5 * desvio
    else:
        corte = 0
    fronteiras = [0]
    for k, s in enumerate(sim):
        i = k + 1  # fronteira entre o parágrafo i-1 e o i
        local = s <= min(sim[max(0, k - 1):k + 2])
        if s < corte and local and i - fronteiras[-1] >= min_paragrafos and len(ps) - i >= min_paragrafos:
            fronteiras.append(i)
    fronteiras.append(len(ps))
    saida: list[Tema] = []
    for a, b in zip(fronteiras, fronteiras[1:]):
        grupo = ps[a:b]
        cont: Counter = Counter()
        for p in grupo:
            cont.update(tokens(p.texto))
        chaves = [w for w, _ in cont.most_common(5)]
        titulo = " / ".join(chaves[:3]) or f"tema {len(saida) + 1}"
        saida.append(Tema(titulo, grupo, chaves))
    return saida
