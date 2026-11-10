"""Etapa 6: palavras -> frases -> parágrafos -> temas.

Frases: pontuação do Whisper + pausas; falas corridas longas (> MAX_PALAVRAS_FRASE) são quebradas na vírgula/pausa
mais forte, para o corte poder começar e terminar em unidades de sentido menores.
Parágrafos e temas: pausas + mudança de sentido. Com a camada semântica (`semantica.py`, e5-small) a fronteira é
onde os vetores das frases vizinhas se afastam (TextTiling com embeddings); sem ela, onde o vocabulário muda.
"""
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
MIN_PALAVRAS_PARAGRAFO = 25   # quebra por mudança de assunto só depois disso
MAX_PALAVRAS_FRASE = 45

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


def _quebrar_longa(ps: list[Palavra]) -> list[list[Palavra]]:
    """Fala corrida de 45+ palavras: divide no ponto mais forte (";", ":", "," com pausa) perto do meio."""
    if len(ps) <= MAX_PALAVRAS_FRASE:
        return [ps]
    melhor, nota_m = None, 0.0
    for k in range(8, len(ps) - 8):
        p, q = ps[k], ps[k + 1]
        nota = 2 * (q.ini - p.fim) + (0.6 if p.texto.endswith((";", ":")) else 0.35 if p.texto.endswith(",") else 0)
        nota -= abs(k - len(ps) / 2) / len(ps) * 0.3
        if nota > nota_m:
            melhor, nota_m = k, nota
    if melhor is None or nota_m < 0.3:
        return [ps]
    return _quebrar_longa(ps[:melhor + 1]) + _quebrar_longa(ps[melhor + 1:])


def frases(palavras: list[Palavra]) -> list[Frase]:
    saida: list[Frase] = []
    atual: list[Palavra] = []
    for i, p in enumerate(palavras):
        atual.append(p)
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        if prox is None or p.texto.endswith(FIM_FRASE) or prox.ini - p.fim >= PAUSA_FRASE:
            saida += [Frase(x) for x in _quebrar_longa(atual)]
            atual = []
    return saida


def paragrafos(fs: list[Frase], vs=None) -> list[Paragrafo]:
    """Quebra em pausa longa, no limite de tamanho ou (com os vetores `vs` das frases) quando o assunto vira:
    a frase seguinte está bem mais longe do parágrafo atual do que o normal desta gravação."""
    import numpy as np
    limiar = None
    if vs is not None and len(fs) > 4:
        viz = np.sum(vs[1:] * vs[:-1], axis=1)
        limiar = float(viz.mean() - 1.0 * viz.std())
    saida: list[Paragrafo] = []
    atual: list[int] = []
    n = 0
    for i, f in enumerate(fs):
        atual.append(i)
        n += len(f.palavras)
        prox = fs[i + 1] if i + 1 < len(fs) else None
        virou = False
        if prox is not None and limiar is not None and n >= MIN_PALAVRAS_PARAGRAFO:
            c = vs[atual].mean(0)
            c /= max(float(np.linalg.norm(c)), 1e-9)
            virou = float(vs[i + 1] @ c) < limiar and float(vs[i + 1] @ vs[i]) < limiar
        if prox is None or prox.ini - f.fim >= PAUSA_PARAGRAFO or n >= MAX_PALAVRAS_PARAGRAFO or virou:
            saida.append(Paragrafo([fs[k] for k in atual]))
            atual, n = [], 0
    return saida


def _cos(a: Counter, b: Counter) -> float:
    num = sum(a[k] * b[k] for k in a if k in b)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def temas(ps: list[Paragrafo], janela: int = 3, min_paragrafos: int = 4, vs_par=None) -> list[Tema]:
    """Fronteira de tema onde o sentido dos parágrafos vizinhos mais muda (TextTiling).

    Com `vs_par` (vetor de cada parágrafo), a similaridade mistura embeddings (70%) e vocabulário (30%)."""
    import numpy as np
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
        lex = _cos(esq, dir_)
        if vs_par is not None:
            a = vs_par[max(0, i - janela):i].mean(0)
            b = vs_par[i:i + janela].mean(0)
            sem = float(a @ b / max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-9))
            sim.append(0.7 * (sem - 0.7) / 0.3 + 0.3 * lex)  # o e5 vive entre ~0,7 e 1: reescala
        else:
            sim.append(lex)
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


def estruturar(palavras: list[Palavra], emb=None, log=None):
    """Frases, parágrafos e temas; com `emb` (semantica.Embeddings) usa sentido além de pausas e vocabulário.

    Retorna (frases, parágrafos, temas, vetores_das_frases | None)."""
    import numpy as np
    fs = frases(palavras)
    vs = None
    if emb is not None and fs:
        from . import cache
        vs, reaproveitado = cache.vetores([f.texto for f in fs], emb.vetores)
        if log:
            log(f"Vetores de sentido de {len(fs)} frases " + ("reaproveitados do cache" if reaproveitado else "calculados"))
    ps = paragrafos(fs, vs)
    vs_par = None
    if vs is not None:
        idx = {id(f): i for i, f in enumerate(fs)}
        vs_par = np.stack([vs[[idx[id(f)] for f in p.frases]].mean(0) for p in ps])
    return fs, ps, temas(ps, vs_par=vs_par), vs
