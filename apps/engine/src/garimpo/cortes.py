"""Etapas 7-8: escolhe os trechos mais relevantes (30 s a 1min30, sem cortar frases).

Seleção em 3 camadas (o mesmo desenho das ferramentas de corte automático: filtrar, pontuar, reordenar com LLM):

1. Filtros duros. Nada de bastidor de gravação (contagem regressiva/progressiva, "gravando", "pronto, vai",
   teste de som), nada de abertura/protocolo do programa ("olá, estamos aqui", "bem-vindos") e nunca começar numa
   frase que depende da anterior. Tudo o que vem antes do último sinal de bastidor dos primeiros minutos é ignorado.
2. Pontuação heurística (rápida, em todas as janelas): **gancho nos 5 primeiros segundos** (peso maior), vocabulário
   raro (TF-IDF), conteúdo concreto (números, exemplos, perguntas, ênfase), duração perto de 1 min.
3. Juiz LLM local (Qwen3-4B em CPU, ver `juiz.py`): relê os melhores candidatos (com a frase de antes e a de
   depois, e a descrição do usuário) e dá notas de gancho, contexto próprio, valor, fechamento e relevância, além
   de poder adiantar o início para a frase mais forte. Sem o modelo, fica a pontuação heurística.

v0.7 (falhas da v0.6: ganchos fracos, fim cortando a fala, contexto fraco):
- **Fechamento é filtro duro** (`fecha_bem`): o corte só termina em fim de frase, com pausa real depois, e nunca
  antes de uma frase que continua a ideia ("porém", "mas", "então", "por isso"...).
- **Camada semântica** (`semantica.py`): relevância para a descrição do vídeo, coesão (uma ideia só) e
  centralidade da oração escolhida como gancho.
- **Gancho**: se a abertura não prende (nota do juiz < 7 ou heurística fraca), o cold open passa a ser obrigatório
  com a oração mais forte e mais central do próprio corte.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .estrutura import _norm, tokens
from .modelos import Corte, Frase, Tema

MIN_S = 30.0
MAX_S = 90.0  # inclui o gancho "cold open"
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
# Ruído de gravação (bastidor): nunca entra em corte.
RUIDO_GRAVACAO = [
    "gravando", "estamos gravando", "to gravando", "ta gravando", "pode gravar", "podemos gravar", "vamos gravar",
    "testando", "teste de som", "teste de audio", "som ok", "audio ok", "microfone ok", "esta rolando", "ta rolando",
    "pode comecar", "podemos comecar", "ja pode", "valendo", "luz ok", "corta ai", "derrubando", "rodando",
    "gravou", "ta gravado", "ja ta", "pode falar", "vamos la", "contagem", "silencio por favor", "som, som",
]
# Palavras de bastidor que só contam em frases curtas ("Pronto.", "Vai!"), para não pegar conteúdo.
BASTIDOR_CURTO = ["pronto", "vai", "bora", "acao", "ok", "beleza", "ja", "foi", "agora", "pode", "certo"]
# Abertura do programa: não é gancho e não pode estar nos primeiros segundos de um corte.
ABERTURA = [
    "ola", "oi pessoal", "fala pessoal", "fala galera", "bom dia", "boa tarde", "boa noite", "sejam bem",
    "bem-vindo", "bem vindo", "estamos aqui", "inaugurando", "mais um episodio", "episodio de hoje", "no podcast",
    "nosso podcast", "meu nome", "eu sou o", "eu sou a", "convidado de hoje", "convidada de hoje", "obrigado por",
    "inscreva", "se inscreve", "deixa o like", "ate a proxima", "ate logo", "um abraco", "tchau",
]
# Bom gancho: pergunta, número, contraste, segunda pessoa, palavras de impacto.
GANCHO_FORTE = [
    "voce", "voces", "ninguem", "nunca", "sempre", "todo mundo", "o problema", "o erro", "a verdade", "o segredo",
    "o maior", "o pior", "o melhor", "o mais", "por que", "porque", "como", "o que", "quanto custa", "custa",
    "dinheiro", "milhoes", "bilhoes", "lei", "direito", "proibido", "obrigatorio", "risco", "perder", "ganhar",
    "mudou", "muda", "acabou", "fim", "cuidado", "atencao", "importante", "imagina", "sabia", "ja pensou",
]
VICIOS_INICIO = ("ne ", "eh ", "e ", "entao ", "bom ", "olha ", "assim ", "tipo ", "ah ", "hum ", "e ai ", "enfim ")
ZONA_BASTIDOR_S = 300.0  # o bastidor costuma estar nos 5 primeiros minutos
JANELA_GANCHO_S = 5.0
PAUSA_CONTEXTO_S = 1.6   # só junta a frase anterior se ela vier logo antes
PAUSA_FIM_S = 0.45       # depois da última frase precisa haver silêncio de verdade (senão a fala é cortada)
PAUSA_FIM_FORTE_S = 1.2  # com pausa assim, nem um "mas" depois impede o fim
# A frase seguinte começa assim: a ideia continua, o corte não pode terminar antes dela.
CONTINUA = ("porem", "mas", "entao", "por isso", "so que", "porque", "pois", "ou seja", "inclusive", "alem disso",
            "e ai", "e", "tanto que", "portanto", "logo", "ai", "agora", "contudo", "entretanto", "inclusive",
            "isso", "nisso", "dai", "ou", "senao", "como", "por exemplo", "tipo", "quer dizer")

_NUMEROS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
            "sete": 7, "oito": 8, "nove": 9, "dez": 10}


def _numeros(texto: str) -> list[int]:
    saida = []
    for tok in re.findall(r"\d+|[a-z]+", texto):
        if tok.isdigit() and len(tok) <= 2:
            saida.append(int(tok))
        elif tok in _NUMEROS:
            saida.append(_NUMEROS[tok])
        else:
            saida.append(-99)  # quebra a sequência
    return saida


def tem_contagem(texto: str) -> bool:
    """3+ números seguidos em ordem (1, 2, 3 ou 5, 4, 3, 2): contagem de bastidor."""
    ns = _numeros(texto)
    for i in range(len(ns) - 2):
        a, b, c = ns[i:i + 3]
        if a >= 0 and ((b == a + 1 and c == b + 1) or (b == a - 1 and c == b - 1)):
            return True
    return False


def _idf(fs: list[Frase]) -> dict[str, float]:
    df: Counter = Counter()
    for f in fs:
        df.update(set(tokens(f.texto)))
    n = max(len(fs), 1)
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def _txt(f: Frase) -> str:
    return _norm(f.texto)


def _limpo(t: str) -> str:
    """Só letras e números, separados por um espaço, com espaço nas pontas (para casar palavras inteiras)."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", _norm(t))) + " "


def _contem(t: str, termos) -> bool:
    lt = _limpo(t)
    return any(f" {_limpo(m).strip()} " in lt for m in termos)


def e_ruido(f: Frase) -> bool:
    """Bastidor de gravação: contagem, "gravando", "pronto, vai" etc."""
    t = _txt(f)
    if tem_contagem(t):
        return True
    if _contem(t, RUIDO_GRAVACAO):
        return True
    palavras = re.findall(r"[a-z]+", t)
    return 0 < len(palavras) <= 4 and all(p in BASTIDOR_CURTO or len(p) <= 2 for p in palavras)


def e_abertura(texto_norm: str) -> bool:
    return _contem(texto_norm, ABERTURA)


def inicio_util(todas: list[Frase]) -> float:
    """Instante a partir do qual a gravação vale: depois do último sinal de bastidor dos primeiros minutos."""
    if not todas:
        return 0.0
    t0 = todas[0].ini
    limite = t0
    for f in todas:
        if f.ini - t0 > ZONA_BASTIDOR_S:
            break
        if e_ruido(f):
            limite = f.fim + 0.01
    return limite


def texto_inicial(fs: list[Frase], janela: float = JANELA_GANCHO_S) -> str:
    """O que se ouve nos primeiros `janela` segundos do corte."""
    ini = fs[0].ini
    return " ".join(p.texto for f in fs for p in f.palavras if p.ini < ini + janela)


def nota_gancho(fs: list[Frase]) -> float:
    """0 a 1: quanto os 5 primeiros segundos prendem. Abertura/protocolo/ruído = 0."""
    t = _norm(texto_inicial(fs))
    if not t or e_abertura(t) or any(e_ruido(f) for f in fs if f.ini < fs[0].ini + JANELA_GANCHO_S):
        return 0.0
    nota = 0.35
    nota += 0.25 * ("?" in t)
    nota += 0.2 * bool(re.search(r"\d", t) or any(f" {n} " in f" {t} " for n in ("mil", "milhoes", "bilhoes")))
    nota += 0.1 * min(sum(_contem(t, [m]) for m in GANCHO_FORTE), 3)
    nota -= 0.25 * _limpo(t).lstrip().startswith(VICIOS_INICIO)
    return max(0.0, min(1.0, nota))


def e_dependente(f: Frase) -> bool:
    """A frase só faz sentido com a anterior: começa em conjunção/referência ou é um fragmento ("Eleitoral.")."""
    lt = _limpo(f.texto).lstrip()
    if lt.startswith(tuple(_limpo(d).lstrip() for d in DEPENDENTES)):
        return True
    return len(lt.split()) < 3 and "?" not in f.texto


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
    gancho = nota_gancho(fs)
    ritmo = max(1.0 - abs(dur - ALVO_S) / ALVO_S, 0.0)
    borda = 0.0
    rel_ini, rel_fim = ini - t0, total_s - (fim - t0)
    if rel_ini < BORDA_S or rel_fim < BORDA_S:
        borda = 1.0
    nota = 1.0 * raro + 0.5 * min(concreto, 3.0) + 2.5 * gancho + 0.8 * ritmo
    nota -= 2.5 * min(protocolo, 3) + 1.5 * borda
    nota -= 3.0 * sum(e_ruido(f) for f in fs)           # bastidor no meio
    nota -= 1.2 * e_dependente(fs[0])                    # começar sem contexto
    return nota


def admissivel(fs: list[Frase], inicio: float = 0.0) -> bool:
    """Filtros duros: o corte só existe se começa limpo, com ideia própria e sem bastidor."""
    if fs[0].ini < inicio or any(e_ruido(f) for f in fs):
        return False
    if e_dependente(fs[0]):
        return False
    return not e_abertura(_norm(texto_inicial(fs)))


def candidatos(tema: Tema, idf: dict[str, float], total_s: float, t0: float, inicio: float | None = None) -> list[Corte]:
    fs = tema.frases
    inicio = t0 if inicio is None else inicio
    saida: list[Corte] = []
    for i in range(len(fs)):
        if fs[i].ini < inicio or e_ruido(fs[i]) or e_dependente(fs[i]):
            continue
        for j in range(i, len(fs)):
            dur = fs[j].fim - fs[i].ini
            if dur > MAX_S or e_ruido(fs[j]):
                break
            if dur >= MIN_S and admissivel(fs[i:j + 1], inicio):
                saida.append(Corte(tema.titulo, fs[i:j + 1], _pontuar(fs[i:j + 1], idf, total_s, t0)))
    return saida


def melhor_corte(tema: Tema, idf: dict[str, float] | None = None, total_s: float = 1e9, t0: float = 0.0) -> Corte | None:
    idf = idf or _idf(tema.frases)
    cs = candidatos(tema, idf, total_s, t0)
    return max(cs, key=lambda c: c.pontuacao) if cs else None


def _termina_frase(f: Frase) -> bool:
    return f.palavras[-1].texto.rstrip().endswith((".", "?", "!", "…"))


def continua_ideia(f: Frase) -> bool:
    """A frase começa retomando a anterior ("Porém...", "E aí...", "Isso..."): a ideia ainda não acabou."""
    lt = _limpo(f.texto).strip()
    return any(lt == c or lt.startswith(c + " ") for c in CONTINUA)


def fecha_bem(ultima: Frase, seguinte: Frase | None) -> bool:
    """O corte pode terminar depois de `ultima`? (filtro duro contra "vídeo encerrado cortando a fala")

    - termina em pontuação final;
    - há silêncio real depois (>= PAUSA_FIM_S) — sem isso o locutor (ou outro) já está falando;
    - a próxima frase não continua a ideia, a menos que venha depois de uma pausa longa."""
    if not _termina_frase(ultima):
        return False
    if seguinte is None:
        return True
    pausa = seguinte.ini - ultima.fim
    if pausa < PAUSA_FIM_S:
        return False
    return pausa >= PAUSA_FIM_FORTE_S or not continua_ideia(seguinte)


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
    if j is not None:
        seg = lambda k: todas[k + 1] if k + 1 < len(todas) else None  # noqa: E731
        # fim: avança até um ponto em que a ideia fecha (sem passar de MAX_S) ...
        k = j
        while not fecha_bem(todas[k], seg(k)) and k + 1 < len(todas) and todas[k + 1].fim - fs[0].ini <= MAX_S \
                and not e_ruido(todas[k + 1]):
            k += 1
        if fecha_bem(todas[k], seg(k)):
            fs += todas[j + 1:k + 1]
        else:
            # ... ou recua até o último ponto que fecha, mantendo a duração mínima
            while len(fs) > 1 and not fecha_bem(fs[-1], seg(pos[id(fs[-1])])) and fs[-2].fim - fs[0].ini >= MIN_S:
                fs.pop()
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
            novo_fim = (t0 + min(calmo) * 0.01 + 0.25) if calmo else fim + 0.40
    if ant_fim is not None:
        novo_ini = max(novo_ini, ant_fim - 0.02) if ant_fim < ini else novo_ini
    if prox_ini is not None and prox_ini > fim:
        novo_fim = min(novo_fim, prox_ini - 0.08)
    return max(novo_ini, 0.0), max(novo_fim, fim)


TEASER_S = (2.0, 7.5)


CONECTIVOS_SOLTOS = {"entao", "e", "mas", "ne", "ai", "olha", "bom", "assim", "tipo", "porque", "que", "eh", "ah"}


def oracoes(f: Frase) -> list[Frase]:
    """Divide uma frase falada (que pode durar 30 s) em orações de 2 a 7,5 s, nas vírgulas e pausas.

    Tira conectivos soltos do começo ("Então,", "E,", "Mas"): a oração vira uma chamada que se sustenta sozinha."""
    partes: list[list] = [[]]
    for k, p in enumerate(f.palavras):
        partes[-1].append(p)
        prox = f.palavras[k + 1] if k + 1 < len(f.palavras) else None
        if prox and (p.texto.endswith((",", ";", ":")) or prox.ini - p.fim > 0.35):
            partes.append([])
    saida: list[Frase] = []
    atual: list = []
    for parte in partes:
        atual += parte
        if not atual:
            continue
        while atual and _limpo(atual[0].texto).strip() in CONECTIVOS_SOLTOS:
            atual.pop(0)
        if atual and atual[-1].fim - atual[0].ini >= TEASER_S[0]:
            saida.append(Frase(list(atual)))
            atual = []
    return [o for o in saida if o.fim - o.ini <= TEASER_S[1] and len(o.palavras) >= 5]


def _centralidade(o: Frase, c: Corte) -> float:
    """0-1: quanto a oração resume o corte (cosseno com o centro do corte, na escala do e5)."""
    from . import semantica
    emb = semantica.carregar()
    if emb is None:
        return 0.5
    vo, vc = emb.vetores([o.texto, c.texto])
    return max(0.0, min(1.0, (float(vo @ vc) - 0.75) / 0.2))


def com_teaser(c: Corte, frase: Frase, log=None, exigir_melhor: bool = False) -> Corte:
    """Põe uma oração de impacto como "cold open" (os primeiros segundos que seguram), sem passar de MAX_S.

    `frase` pode ser longa: escolhe dentro dela a oração com o gancho mais forte."""
    candidatas = [frase] if TEASER_S[0] <= frase.fim - frase.ini <= TEASER_S[1] else []
    candidatas += oracoes(frase)
    candidatas = [o for o in candidatas if len(o.palavras) >= 5 and not e_ruido(o) and not e_abertura(_norm(o.texto))
                  and o.ini >= c.ini + 3.0 and o.fim <= c.fim]
    if not candidatas:
        return c
    o = max(candidatas, key=lambda x: (nota_gancho([x]) + 0.4 * _centralidade(x, c) - 0.05 * abs((x.fim - x.ini) - 4.5)))
    if exigir_melhor and nota_gancho([o]) <= nota_gancho(c.frases):
        return c  # heurística: só vale se o gancho prende mais do que a abertura original
    dur = o.fim - o.ini
    fs = list(c.frases)
    while fs[-1].fim - fs[0].ini + dur + 0.3 > MAX_S and len(fs) > 1 and fs[-2].fim - fs[0].ini >= MIN_S             and fs[-2].fim > o.fim:
        fs.pop()
    if fs[-1].fim - fs[0].ini + dur + 0.3 > MAX_S:
        return c
    if log:
        log(f"    gancho “cold open”: “{o.texto[:80]}”")
    return Corte(c.tema, fs, c.pontuacao, teaser=o)


def teaser_heuristico(c: Corte, log=None, forcar: bool = False) -> Corte:
    """A oração (após os 8 s iniciais) com o gancho mais forte e mais central. Por padrão só entra se prender mais
    que a abertura; com `forcar` (abertura fraca segundo o juiz) entra sempre que houver uma oração boa."""
    ors = [o for f in c.frases for o in oracoes(f) if o.ini - c.ini >= 8]
    if not ors:
        return c
    melhor = max(ors, key=lambda o: nota_gancho([o]) + 0.3 * _centralidade(o, c))
    if forcar and nota_gancho([melhor]) >= 0.45:
        return com_teaser(c, melhor, log)
    return com_teaser(c, melhor, log, exigir_melhor=True)


def _sobrepoe(a: Corte, b: Corte, folga: float = 0.0) -> bool:
    return not (a.fim <= b.ini + folga or a.ini >= b.fim - folga)


def _semantica(lista: list[Corte], todas: list[Frase], vs, descricao: str, log=None) -> None:
    """Soma à pontuação: relevância para a descrição do usuário (peso 3) e coesão do trecho (peso 1,5)."""
    import numpy as np

    from . import semantica
    if vs is None or not lista:
        return
    idx = {id(f): i for i, f in enumerate(todas)}
    q = None
    if descricao.strip():
        emb = semantica.carregar()
        q = emb.vetores([descricao], "query")[0] if emb else None
    rel = []
    for c in lista:
        v = vs[[idx[id(f)] for f in c.frases if id(f) in idx]]
        if not len(v):
            rel.append(0.0)
            continue
        c.pontuacao += 1.5 * max(0.0, (semantica.coesao(v) - 0.8) / 0.15)
        rel.append(float(semantica.centro(v) @ q) if q is not None else 0.0)
    if q is not None:
        r = np.array(rel)
        z = (r - r.mean()) / max(float(r.std()), 1e-6)
        for c, zi in zip(lista, z):
            c.pontuacao += 1.0 * float(np.clip(zi, -2, 2))
            c.relevancia = float(zi)
        if log:
            log(f"Relevância para a descrição calculada em {len(lista)} janelas")


def sugerir(temas: list[Tema], por_minutos: float = 7.0, juiz=None, log=None, descricao: str = "",
            vs=None) -> list[Corte]:
    """Escolhe os cortes: filtros duros -> heurística (+ semântica) em todas as janelas -> juiz LLM nos melhores.

    `descricao`: o que o usuário escreveu sobre o vídeo (tema, público, objetivo) — guia a relevância.
    `vs`: vetores das frases (mesma ordem das frases dos temas), da camada semântica."""
    todas = [f for t in temas for f in t.frases]
    if not todas:
        return []
    idf = _idf(todas)
    t0, total = todas[0].ini, todas[-1].fim - todas[0].ini
    inicio = inicio_util(todas)
    if log and inicio > t0:
        log(f"Bastidor de gravação detectado: ignorando tudo antes de {inicio - t0:.1f}s")
    # menos e melhores: ~1 corte a cada 8 min de gravação (mín. 3, máx. 10)
    quota = max(3, min(10, round(total / 480)))

    # 1-2: candidatos válidos e pontuados; melhores sem sobreposição (diversidade entre temas)
    por_tema: dict[str, int] = {}
    lista: list[Corte] = []
    for t in temas:
        lista += [completar_contexto(c, todas, inicio) for c in candidatos(t, idf, total, t0, inicio)]
    pos = {id(f): i for i, f in enumerate(todas)}
    seguinte = lambda f: todas[pos[id(f)] + 1] if pos[id(f)] + 1 < len(todas) else None  # noqa: E731
    antes = len(lista)
    lista = [c for c in lista if admissivel(c.frases, inicio) and MIN_S <= c.duracao <= MAX_S
             and fecha_bem(c.frases[-1], seguinte(c.frases[-1]))]
    if log:
        log(f"{antes - len(lista)} janela(s) descartada(s) por não fechar a ideia ou cortar a fala")
    _semantica(lista, todas, vs, descricao, log)
    lista.sort(key=lambda c: -c.pontuacao)
    curtos: list[Corte] = []
    vaga = min(max(quota + 6, int(quota * 1.3)), 24) if juiz else quota  # ~15 s por finalista em CPU
    for c in lista:
        if len(curtos) >= vaga:
            break
        if por_tema.get(c.tema, 0) >= (3 if juiz else 2) or any(_sobrepoe(c, p) for p in curtos):
            continue
        curtos.append(c)
        por_tema[c.tema] = por_tema.get(c.tema, 0) + 1
    if log:
        log(f"{len(lista)} janelas válidas; {len(curtos)} finalistas para {quota} corte(s)")

    # 3: juiz LLM reordena (e pode adiantar o início para a frase mais forte)
    if juiz and curtos:
        avaliados = []
        for k, c in enumerate(curtos, 1):
            i0 = pos[id(c.frases[0])]
            r = juiz.avaliar(c, antes=todas[i0 - 1] if i0 > 0 else None, depois=seguinte(c.frases[-1]),
                             descricao=descricao)
            if log:
                log(f"  Juiz {k}/{len(curtos)}: nota {r.nota:.1f} (gancho {r.gancho}, contexto {r.contexto}, valor {r.valor}, fim {r.fechamento}, relevância {r.relevancia})"
                    + (" [bastidor]" if r.bastidor else "") + f" — “{c.texto[:70]}…”")
            if r.bastidor or r.fechamento < 4:
                continue
            novo = c
            if 0 < r.inicio < len(c.frases):
                cand = Corte(c.tema, c.frases[r.inicio:], c.pontuacao)
                if cand.duracao >= MIN_S and admissivel(cand.frases, inicio):
                    novo = cand
                    if log:
                        log(f"    início adiantado para a frase {r.inicio + 1}: “{cand.texto[:60]}…”")
            novo.pontuacao = r.nota + 0.1 * c.pontuacao
            impacto = c.frases[r.impacto] if 0 <= r.impacto < len(c.frases) else None
            # gancho fraco na abertura: o cold open é obrigatório (oração mais forte e central do corte)
            if impacto is not None and impacto is not novo.frases[0]:
                novo = com_teaser(novo, impacto, log, exigir_melhor=r.gancho >= 7)
            if novo.teaser is None:
                novo = teaser_heuristico(novo, log, forcar=r.gancho < 7)
            avaliados.append(novo)
        curtos = sorted(avaliados, key=lambda c: -c.pontuacao)
        # nota mínima: só passa o que o juiz considera bom (mantém ao menos 3)
        bons = [c for c in curtos if c.pontuacao >= 5.6]
        curtos = bons if len(bons) >= 3 else curtos[:max(3, len(bons))]

    if not juiz:
        curtos = [teaser_heuristico(c) for c in curtos]
    final: list[Corte] = []
    contagem: dict[str, int] = {}
    for c in curtos:
        if len(final) >= quota:
            break
        if contagem.get(c.tema, 0) >= 2 or any(_sobrepoe(c, p) for p in final):
            continue
        final.append(c)
        contagem[c.tema] = contagem.get(c.tema, 0) + 1
    return sorted(final, key=lambda c: c.ini)
