"""Legenda dinâmica palavra por palavra (ASS): Lato em MAIÚSCULAS, branca, 64 px, 1080x1920.

Motion inspirado na referência (desfoque cinematográfico):
- entrada: a palavra nasce desfocada, transparente, 100 px acima e levemente menor; em ~0,5 s assenta no
  lugar com easing exponencial (rápida no começo, macia no fim) enquanto o desfoque some;
- saída: pouco antes da próxima palavra, ela se dissolve (desfoque + fade + leve queda), cruzando com a entrada
  da seguinte, como no vídeo de referência;
- glow fixo: duas camadas brancas desfocadas atrás do texto nítido, sem nenhum traçado.

A animação é desenhada a 60 quadros por segundo (um evento por quadro), então fica suave em vídeos de 24/30/60 fps.
"""
from __future__ import annotations

import math
from pathlib import Path

from .modelos import Corte

BRANCO = "&H00FFFFFF"
FONTE = "Lato"
TAMANHO = 64          # px (PlayRes 1080x1920)
X, Y = 540, 1400      # centro da legenda
ENTRADA = 0.50        # s
SAIDA = 0.16          # s (sobrepõe a entrada da próxima palavra)
SOBREPOSICAO = 0.08   # s em que a saída de uma e a entrada da outra se cruzam
DESLOCAMENTO = 100    # px: começa 100 px acima
QUEDA_SAIDA = 18      # px que a palavra desce ao sair
ESCALA_INICIAL = 0.90
DESFOQUE_ENTRADA = 10.0
DESFOQUE_SAIDA = 8.0
PASSO = 1 / 60

# (borda, blur, transparência ASS: 0 = opaco, 255 = invisível). Valores fixos: o glow não anima.
GLOW = [(24, 28, 200), (10, 12, 150)]


def _t(s: float) -> str:
    cs = int(round(max(s, 0.0) * 100))
    h, resto = divmod(cs, 360000)
    m, resto = divmod(resto, 6000)
    seg, c = divmod(resto, 100)
    return f"{h}:{m:02d}:{seg:02d}.{c:02d}"


def ease_out_expo(p: float) -> float:
    """Desacelera forte no fim: movimento que "assenta"."""
    return 1.0 if p >= 1 else 1 - math.pow(2, -10 * p)


def ease_in_cubic(p: float) -> float:
    return p ** 3


def _alfa(base: int, opacidade: float) -> str:
    return f"&H{round(255 - (255 - base) * max(0.0, min(1.0, opacidade))):02X}&"


def _evento(camada: int, ini: float, fim: float, texto: str, y: float, opac: float, blur: float, escala: float,
            borda: int, base: int) -> str:
    a = _alfa(base, opac)
    tags = (f"\\an5\\pos({X},{y:.1f})\\fscx{escala * 100:.1f}\\fscy{escala * 100:.1f}"
            f"\\bord{borda}\\shad0\\blur{blur:.1f}\\3c{BRANCO}\\1a{a}\\3a{a}")
    return f"Dialogue: {camada},{_t(ini)},{_t(fim)},Padrao,,0,0,0,,{{{tags}}}{texto}"


def _estado(t: float, dur: float, tem_saida: bool) -> tuple[float, float, float, float]:
    """(y, opacidade, desfoque extra, escala) no instante t (s desde o início da palavra)."""
    p = min(t / ENTRADA, 1.0)
    e = ease_out_expo(p)
    y = Y - DESLOCAMENTO * (1 - e)
    opac = min(1.0, p * 1.8) if p < 1 else 1.0         # aparece logo no começo do movimento
    desfoque = DESFOQUE_ENTRADA * (1 - e)
    escala = ESCALA_INICIAL + (1 - ESCALA_INICIAL) * e
    if tem_saida and t > dur - SAIDA:
        q = ease_in_cubic(min((t - (dur - SAIDA)) / SAIDA, 1.0))
        y += QUEDA_SAIDA * q
        opac *= 1 - q
        desfoque += DESFOQUE_SAIDA * q
    return y, opac, desfoque, escala


def _palavra(ini: float, fim: float, texto: str, tem_saida: bool) -> list[str]:
    linhas: list[str] = []
    camadas = [(i, b, bl, a) for i, (b, bl, a) in enumerate(GLOW)] + [(len(GLOW), 0, 0.5, 0)]
    dur = fim - ini
    animado_ate = min(ENTRADA, dur)
    inicio_saida = dur - SAIDA if tem_saida else dur
    # quadros animados: entrada e saída; entre elas, um evento parado
    marcos = [k * PASSO for k in range(int(animado_ate / PASSO))]
    parado = (animado_ate, inicio_saida) if inicio_saida > animado_ate else None
    if tem_saida:
        k0 = max(animado_ate, inicio_saida)
        marcos += [k0 + k * PASSO for k in range(int((dur - k0) / PASSO) + 1) if k0 + k * PASSO < dur]
    marcos = sorted(set(round(m, 4) for m in marcos))
    for k, t in enumerate(marcos):
        prox = marcos[k + 1] if k + 1 < len(marcos) else t + PASSO
        if parado and t < parado[0] <= prox:
            prox = parado[0]
        prox = min(prox, dur)
        if prox <= t:
            continue
        y, opac, desf, esc = _estado(t, dur, tem_saida)
        for camada, borda, blur, base in camadas:
            linhas.append(_evento(camada, ini + t, ini + prox, texto, y, opac, blur + desf, esc, borda, base))
    if parado:
        for camada, borda, blur, base in camadas:
            linhas.append(_evento(camada, ini + parado[0], ini + parado[1], texto, Y, 1.0, blur, 1.0, borda, base))
    return linhas


def gerar_ass(corte: Corte, caminho: Path, origem: float | None = None) -> Path:
    """Legenda palavra por palavra. `origem` é o instante do vídeo onde o corte começa (padrão: 1ª palavra)."""
    origem = corte.ini if origem is None else origem
    cab = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,"
        "MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Padrao,{FONTE},{TAMANHO},{BRANCO},{BRANCO},{BRANCO},&HFF000000,-1,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    palavras = [p for f in corte.frases for p in f.palavras]
    linhas: list[str] = []
    for k, w in enumerate(palavras):
        ini = max(w.ini - origem, 0.0)
        ultima = k + 1 >= len(palavras)
        # a palavra fica até a próxima começar (+ um cruzamento curto); a última fica até o fim da fala
        fim = (w.fim + 0.4 if ultima else palavras[k + 1].ini + SOBREPOSICAO) - origem
        fim = max(fim, ini + 0.12)
        linhas += _palavra(ini, fim, w.texto.upper(), tem_saida=not ultima)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho
