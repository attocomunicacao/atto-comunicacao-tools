"""Legenda dinâmica palavra por palavra (ASS): Lato em MAIÚSCULAS, branca, 64 px, 1080x1920.

Uma palavra por vez. Cada palavra entra com opacidade 0 -> 100%, deslocamento em y de -100 px -> 0 e um
leve desfoque que some, tudo com easing (ease-out), desenhado quadro a quadro. O glow é fixo: duas camadas
brancas desfocadas (uma larga e suave, outra curta) por trás do texto nítido, sem nenhum traçado.
"""
from __future__ import annotations

from pathlib import Path

from .modelos import Corte

BRANCO = "&H00FFFFFF"
FONTE = "Lato"
TAMANHO = 64          # px (PlayRes 1080x1920)
X, Y = 540, 1400      # centro da legenda
ENTRADA = 0.42        # s: duração da animação de entrada
DESLOCAMENTO = 100    # px: começa 100 px acima e desce até o lugar
DESFOQUE_ENTRADA = 7  # px de blur no primeiro quadro, some com a entrada
PASSO = 1 / 30        # s: um evento por quadro durante a entrada

# (borda, blur, transparência ASS: 0 = opaco, 255 = invisível). Valores fixos: o glow não anima.
GLOW = [(26, 30, 205), (11, 14, 160)]


def _t(s: float) -> str:
    s = max(s, 0.0)
    cs = int(round(s * 100))
    h, resto = divmod(cs, 360000)
    m, resto = divmod(resto, 6000)
    seg, c = divmod(resto, 100)
    return f"{h}:{m:02d}:{seg:02d}.{c:02d}"


def _ease_out(p: float) -> float:
    """Desacelera no fim (cúbica): movimento rápido que assenta macio."""
    return 1 - (1 - p) ** 3


def _alfa(base: int, opacidade: float) -> str:
    """Transparência ASS para uma camada de transparência `base` com a opacidade global da animação."""
    return f"&H{round(255 - (255 - base) * opacidade):02X}&"


def _evento(camada: int, ini: float, fim: float, texto: str, y: float, opac: float, blur: float,
            borda: int = 0, base: int = 0) -> str:
    tags = f"\\an5\\pos({X},{y:.1f})\\bord{borda}\\shad0\\blur{blur:.1f}\\3c{BRANCO}\\1a{_alfa(base, opac)}\\3a{_alfa(base, opac)}"
    return f"Dialogue: {camada},{_t(ini)},{_t(fim)},Padrao,,0,0,0,,{{{tags}}}{texto}"


def _palavra(ini: float, fim: float, texto: str) -> list[str]:
    linhas: list[str] = []
    camadas = [(i, b, bl, a) for i, (b, bl, a) in enumerate(GLOW)] + [(len(GLOW), 0, 0.4, 0)]
    entrada = min(ENTRADA, max(fim - ini, PASSO))
    n = max(int(round(entrada / PASSO)), 1)
    for k in range(n):
        a, b = ini + k * entrada / n, ini + (k + 1) * entrada / n
        p = k / n  # o 1º quadro parte exatamente de y-100 e opacidade 0
        suave = _ease_out(p)
        y = Y - DESLOCAMENTO * (1 - suave)
        opac = min(1.0, suave * 1.15)
        for camada, borda, blur, base in camadas:
            desfoque = blur + (DESFOQUE_ENTRADA * (1 - suave) ** 2 if camada == len(GLOW) else 0)
            linhas.append(_evento(camada, a, b, texto, y, opac, desfoque, borda, base))
    if fim > ini + entrada:
        for camada, borda, blur, base in camadas:
            linhas.append(_evento(camada, ini + entrada, fim, texto, Y, 1.0, blur, borda, base))
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
        ini = w.ini - origem
        fim = (palavras[k + 1].ini if k + 1 < len(palavras) else w.fim) - origem
        linhas += _palavra(max(ini, 0.0), max(fim, ini + 0.05, 0.05), w.texto.upper())
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho
