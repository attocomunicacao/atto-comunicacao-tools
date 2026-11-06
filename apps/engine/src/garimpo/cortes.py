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
# Frases que dependem do que veio antes: o corte não pode começar nelas (falta contexto).
DEPENDENTES = CONJUNCOES + (
    "isso ", "isto ", "essa ", "esse ", "essas ", "esses ", "nisso ", "nessa ", "nesse ", "disso ", "dessa ",
    "desse ", "por isso", "por isso,", "tambem ", "alem disso", "ou seja", "dai ", "pois ", "porem ", "contudo",
    "entretanto", "inclusive", "aquilo ", "ele ", "ela ", "eles ", "elas ", "la ", "ali ", "assim ", "logo ",
    "portanto", "e a ", "e o ", "mas a ", "mas o ")
# Ruído de gravação (teste de som, "gravando"): nunca entra em corte nos primeiros minutos e é penalizado depois.
RUIDO_GRAVACAO = [
    "gravando", "estamos gravando", "to gravando", "ta gravando", "pode gravar", "podemos gravar", "vamos gravar",
    "testando", "teste de som", "teste de audio", "som ok", "audio ok", "microfone ok", "esta rolando", "ta rolando",
    "pode comecar", "podemos comecar", "ja pode", "valendo", "camera", "luz ok", "cortar", "corta ai", "um dois tres",
    "tres dois um", "1 2 3", "1, 2, 3", "3, 2, 1", "check", "som, som",
]
ZONA_RUIDO_S = 600.0  # 10 min iniciais: qualquer sinal de ruído exclui o trecho
PAUSA_CONTEXTO_S = 1.6  # só junta a frase anterior se ela vier logo antes


def _idf(fs: list[Frase]) -> dict[str, float]:
    df: Counter = Counter()
    for f in fs:
        df.update(set(tokens(f.texto)))
    n = max(len(fs), 1)
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def _txt(f: Frase) -> str:
    return _norm(f.texto)


_CONTAGEM = re.compile(r'(?<!\d)1\W{1,3}2\W{1,3}3(?!\d)|um\W{1,3}dois\W{1,3}tres')


def e_ruido(f: Frase) -> bool:
    t = _txt(f) + " "
    if _CONTAGEM.search(t):
        return True
    return any(m in t for m in RUIDO_GRAVACAO)


def e_dependente(f: Frase) -> bool:
    """A frase só faz sentido com a anterior (começa em conjunção ou referência)."""
    return (_txt(f) + " ").startswith(DEPENDENTES)


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
    nota -= 3.0 * sum(e_ruido(f) for f in fs)           # teste de som e afins
    nota -= 1.2 * e_dependente(fs[0])                    # começar sem contexto
    return nota


def candidatos(tema: Tema, idf: dict[str, float], total_s: float, t0: float) -> list[Corte]:
    fs = tema.frases
    saida: list[Corte] = []
    for i in range(len(fs)):
        for j in range(i, len(fs)):
            dur = fs[j].fim - fs[i].ini
            if dur > MAX_S:
                break
            if j > i and e_ruido(fs[j]) and fs[j].ini - t0 < ZONA_RUIDO_S:
                break  # ruído de gravação no começo: o trecho acaba antes dele
            if e_ruido(fs[i]) and fs[i].ini - t0 < ZONA_RUIDO_S:
                break
            if dur >= MIN_S:
                saida.append(Corte(tema.titulo, fs[i:j + 1], _pontuar(fs[i:j + 1], idf, total_s, t0)))
    return saida


def melhor_corte(tema: Tema, idf: dict[str, float] | None = None, total_s: float = 1e9, t0: float = 0.0) -> Corte | None:
    idf = idf or _idf(tema.frases)
    cs = candidatos(tema, idf, total_s, t0)
    return max(cs, key=lambda c: c.pontuacao) if cs else None


def _termina_frase(f: Frase) -> bool:
    return f.palavras[-1].texto.rstrip().endswith((".", "?", "!", "…"))


def completar_contexto(c: Corte, todas: list[Frase], limite_ini: float = 0.0) -> Corte:
    """Garante um corte que abre com a ideia inteira e fecha em frase completa.

    - se a 1ª frase depende da anterior ("isso", "mas", "então"...), puxa as frases de antes (até 3);
    - se mesmo assim não der (passaria de MAX_S), descarta a frase dependente do começo;
    - se a última frase não termina em pontuação, junta a seguinte."""
    fs = list(c.frases)
    pos = {id(f): i for i, f in enumerate(todas)}
    i0 = pos.get(id(fs[0]))
    if i0 is None:
        return c
    puxadas = 0
    while e_dependente(fs[0]) and i0 > 0 and puxadas < 3:
        ant = todas[i0 - 1]
        if fs[0].ini - ant.fim > PAUSA_CONTEXTO_S or ant.ini < limite_ini or e_ruido(ant):
            break
        fs.insert(0, ant)
        i0 -= 1
        puxadas += 1
    while fs[-1].fim - fs[0].ini > MAX_S and len(fs) > 1:
        # estourou: tira do fim se o começo já está completo, senão tira o começo dependente
        if e_dependente(fs[0]) and puxadas == 0:
            fs.pop(0)
        else:
            fs.pop()
    while e_dependente(fs[0]) and len(fs) > 1 and fs[-1].fim - fs[1].ini >= MIN_S:
        fs.pop(0)
    j = pos.get(id(fs[-1]), None)
    while j is not None and not _termina_frase(fs[-1]) and j + 1 < len(todas)             and todas[j + 1].ini - fs[-1].fim <= PAUSA_CONTEXTO_S and todas[j + 1].fim - fs[0].ini <= MAX_S + 15:
        j += 1
        fs.append(todas[j])
    return Corte(c.tema, fs, c.pontuacao)


def _energia(wav, ini: float, fim: float):
    """RMS por janelas de 10 ms entre ini e fim (s) de um WAV mono 16 bits. Retorna (inicio_real, vetor)."""
    import numpy as np
    sr = wav["sr"]
    a, b = max(int(ini * sr), 0), min(int(fim * sr), len(wav["x"]))
    if b - a < sr // 50:
        return a / sr, np.zeros(0)
    passo = sr // 100
    x = wav["x"][a:b].astype(np.float32)
    n = len(x) // passo
    return a / sr, np.sqrt((x[:n * passo].reshape(n, passo) ** 2).mean(axis=1))


def carregar_wav(caminho):
    import wave

    import numpy as np
    with wave.open(str(caminho), "rb") as w:
        return {"sr": w.getframerate(), "x": np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)}


def ajustar_limites(ini: float, fim: float, ant_fim: float | None, prox_ini: float | None, wav) -> tuple[float, float]:
    """Move o início/fim do corte para um instante de silêncio, para nunca começar ou acabar no meio de uma palavra.

    O Whisper erra os tempos em 100-200 ms: por isso procura, no áudio, o ponto mais calmo perto da fronteira."""
    import numpy as np
    novo_ini, novo_fim = ini - 0.15, fim + 0.20     # folga mínima, caso não haja áudio
    if wav is not None:
        t0, e = _energia(wav, ini - 0.45, ini + 0.05)
        if len(e):
            ref = max(float(np.percentile(_energia(wav, ini, ini + 0.6)[1], 80)), 1.0)
            calmo = [k for k in range(len(e)) if e[k] < 0.12 * ref]
            antes = [k for k in calmo if t0 + k * 0.01 <= ini - 0.03]
            if antes:
                novo_ini = t0 + max(antes) * 0.01 - 0.02      # último trecho calmo antes da palavra
            else:
                novo_ini = ini - 0.30
        t0, e = _energia(wav, fim - 0.05, fim + 0.55)
        if len(e):
            ref = max(float(np.percentile(_energia(wav, fim - 0.6, fim)[1], 80)), 1.0)
            calmo = [k for k in range(len(e)) if e[k] < 0.12 * ref and t0 + k * 0.01 >= fim + 0.02]
            novo_fim = (t0 + min(calmo) * 0.01 + 0.10) if calmo else fim + 0.35
    if ant_fim is not None:
        novo_ini = max(novo_ini, ant_fim - 0.02) if ant_fim < ini else novo_ini
    if prox_ini is not None and prox_ini > fim:
        novo_fim = min(novo_fim, prox_ini - 0.02)
    return max(novo_ini, 0.0), max(novo_fim, fim)


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
    # contexto e fim em frase completa, sem invadir o corte anterior
    saida: list[Corte] = []
    for c in sorted(escolhidos, key=lambda c: c.ini):
        c = completar_contexto(c, todas, limite_ini=saida[-1].fim if saida else 0.0)
        if saida and c.ini < saida[-1].fim:
            continue
        saida.append(c)
    return saida
