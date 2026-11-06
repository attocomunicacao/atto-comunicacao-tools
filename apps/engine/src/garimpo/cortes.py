"""Etapas 7-8: escolhe os trechos mais relevantes (30 s a 1min30, sem cortar frases).

A pontuação combina, sem LLM (rápido em CPU):
- vocabulário raro na palestra inteira (TF-IDF), em vez de palavras comuns do tema;
- gancho: a primeira frase abre com uma ideia, não com conjunção ("e", "então", "mas");
- conteúdo concreto: números, exemplos, perguntas, marcadores de ênfase;
- penalidade para saudações, agradecimentos, apresentações e passagem de palavra;
- penalidade para o início e o fim da gravação (abertura e encerramento do evento).
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .estrutura import _norm, tokens
from .modelos import Corte, Frase, Tema

MIN_S = 30.0
MAX_S = 90.0
ALVO_S = 60.0
BORDA_S = 180.0  # primeiros e últimos 3 min da gravação costumam ser protocolo

FORMULAS = [
    "bom dia", "boa tarde", "boa noite", "meu nome", "obrigado", "obrigada", "agradec", "passar a palavra",
    "passo a palavra", "palavra para", "palavra ao", "sejam bem", "bem-vindo", "bem vindo", "aplausos",
    "microfone", "pode ouvir", "estao me ouvindo", "vamos comecar", "para comecar", "ate logo", "ate a proxima",
]
ENFASE = [
    "importante", "atencao", "cuidado", "na pratica", "por exemplo", "o que muda", "ou seja", "isso significa",
    "o principal", "o mais", "erro", "direito", "obrigatorio", "proibido", "nunca", "sempre", "regra", "risco",
    "garantia", "como funciona", "o segredo", "a verdade", "na verdade",
]
CONJUNCOES = ("e ", "mas ", "entao ", "ai ", "porque ", "ou ", "so que ", "tipo ")


def _idf(fs: list[Frase]) -> dict[str, float]:
    df: Counter = Counter()
    for f in fs:
        df.update(set(tokens(f.texto)))
    n = max(len(fs), 1)
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def _pontuar(fs: list[Frase], idf: dict[str, float], total_s: float, t0: float) -> float:
    palavras = sum(len(f.palavras) for f in fs)
    ini, fim = fs[0].ini, fs[-1].fim
    dur = fim - ini
    if palavras == 0 or dur <= 0:
        return 0.0
    texto = _norm(" ".join(f.texto for f in fs))
    toks = tokens(texto)
    raro = sum(idf.get(t, 1.0) for t in toks) / palavras  # densidade de vocabulário informativo
    concreto = (
        0.5 * len(re.findall(r"\d+", texto)) / (palavras / 50)
        + 0.4 * sum(texto.count(m) for m in ENFASE) / (palavras / 50)
        + 0.3 * texto.count("?") / (palavras / 50)
    )
    protocolo = sum(texto.count(m) for m in FORMULAS)
    abertura = _norm(fs[0].texto)
    gancho = 0.0 if abertura.startswith(CONJUNCOES) else 1.0
    ritmo = max(1.0 - abs(dur - ALVO_S) / ALVO_S, 0.0)
    borda = 0.0
    rel_ini, rel_fim = ini - t0, total_s - (fim - t0)
    if rel_ini < BORDA_S or rel_fim < BORDA_S:
        borda = 1.0
    nota = 1.0 * raro + 0.5 * min(concreto, 3.0) + 0.6 * gancho + 0.8 * ritmo
    nota -= 2.5 * min(protocolo, 3) + 1.5 * borda
    return nota


def candidatos(tema: Tema, idf: dict[str, float], total_s: float, t0: float) -> list[Corte]:
    fs = tema.frases
    saida: list[Corte] = []
    for i in range(len(fs)):
        for j in range(i, len(fs)):
            dur = fs[j].fim - fs[i].ini
            if dur > MAX_S:
                break
            if dur >= MIN_S:
                saida.append(Corte(tema.titulo, fs[i:j + 1], _pontuar(fs[i:j + 1], idf, total_s, t0)))
    return saida


def melhor_corte(tema: Tema, idf: dict[str, float] | None = None, total_s: float = 1e9, t0: float = 0.0) -> Corte | None:
    idf = idf or _idf(tema.frases)
    cs = candidatos(tema, idf, total_s, t0)
    return max(cs, key=lambda c: c.pontuacao) if cs else None


def sugerir(temas: list[Tema], por_minutos: float = 7.0) -> list[Corte]:
    """Melhores cortes sem sobreposição: 1 por tema e mais 1 a cada `por_minutos` de tema, em ordem cronológica."""
    todas = [f for t in temas for f in t.frases]
    if not todas:
        return []
    idf = _idf(todas)
    t0, total = todas[0].ini, todas[-1].fim - todas[0].ini
    escolhidos: list[Corte] = []
    for t in temas:
        quota = 1 + int((t.fim - t.ini) // (por_minutos * 60))
        cands = sorted(candidatos(t, idf, total, t0), key=lambda c: -c.pontuacao)
        pegos: list[Corte] = []
        for c in cands:
            if len(pegos) >= quota:
                break
            if all(c.fim <= p.ini or c.ini >= p.fim for p in pegos):
                pegos.append(c)
        escolhidos += pegos
    return sorted(escolhidos, key=lambda c: c.ini)
