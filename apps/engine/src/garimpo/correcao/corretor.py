"""Correção determinística: encontra trechos parecidos (no som e na escrita) com termos do dicionário."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from .dicionario import Dicionario

_PALAVRA = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def chave_fonetica(texto: str) -> str:
    """Forma simplificada que aproxima palavras de som parecido (ex.: 'Cinti Preste' ~ 'SINDEPRESTEM')."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z]", "", t)
    t = re.sub(r"c(?=[ei])", "s", t)
    t = t.replace("ss", "s").replace("sc", "s").replace("ch", "x").replace("qu", "k")
    t = t.replace("c", "k").replace("z", "s").replace("h", "")
    t = t.translate(str.maketrans("dbgvoe", "tpkfui"))
    t = re.sub(r"(.)\1+", r"\1", t)
    return t


@dataclass
class Sugestao:
    inicio: int  # posição no texto
    fim: int
    original: str
    sugestao: str
    confianca: float
    conhecida: bool  # variante já confirmada antes pelo usuário


def _janelas(texto: str, maximo: int = 3):
    palavras = list(_PALAVRA.finditer(texto))
    for i in range(len(palavras)):
        for n in range(1, maximo + 1):
            if i + n > len(palavras):
                break
            ini, fim = palavras[i].start(), palavras[i + n - 1].end()
            yield ini, fim, texto[ini:fim]


def sugerir(texto: str, dic: Dicionario, limiar: float = 0.8) -> list[Sugestao]:
    """Devolve sugestões sem sobreposição, da mais confiável para a menos."""
    candidatas: list[Sugestao] = []
    chaves = {t: chave_fonetica(t) for t in dic.termos}
    variantes = {v.lower(): t for t, vs in dic.termos.items() for v in vs}
    for ini, fim, trecho in _janelas(texto):
        if trecho.lower() in variantes:
            candidatas.append(Sugestao(ini, fim, trecho, variantes[trecho.lower()], 1.0, True))
            continue
        k = chave_fonetica(trecho)
        if len(k) < 4:
            continue
        for termo, kt in chaves.items():
            if termo.lower() in trecho.lower():  # já contém o termo correto
                continue
            if abs(len(k) - len(kt)) > max(2, len(kt) // 4):
                continue
            r = SequenceMatcher(None, k, kt).ratio()
            if r >= limiar:
                candidatas.append(Sugestao(ini, fim, trecho, termo, round(r, 3), False))
    candidatas.sort(key=lambda s: (-s.confianca, -(s.fim - s.inicio)))
    escolhidas: list[Sugestao] = []
    for c in candidatas:
        if all(c.fim <= e.inicio or c.inicio >= e.fim for e in escolhidas):
            escolhidas.append(c)
    return sorted(escolhidas, key=lambda s: s.inicio)


def aplicar(texto: str, aprovadas: list[Sugestao]) -> str:
    for s in sorted(aprovadas, key=lambda s: s.inicio, reverse=True):
        texto = texto[: s.inicio] + s.sugestao + texto[s.fim :]
    return texto
