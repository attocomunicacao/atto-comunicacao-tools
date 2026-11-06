"""Legenda dinâmica palavra por palavra (ASS), Lato em MAIÚSCULAS, 1080x1920."""
from __future__ import annotations

from pathlib import Path

from .modelos import Corte

BRANCO = "&H00FFFFFF"
TAMANHO = 48          # px (PlayRes 1080x1920)
X, Y = 540, 1400      # centro da legenda
ENTRADA_MS = 300      # animação de entrada: opacidade 0 -> 100% e y -100 px -> 0
DESLOCAMENTO = 100


def _t(s: float) -> str:
    s = max(s, 0.0)
    h, resto = divmod(s, 3600)
    m, seg = divmod(resto, 60)
    return f"{int(h)}:{int(m):02d}:{seg:05.2f}"


def gerar_ass(corte: Corte, caminho: Path) -> Path:
    """Legenda palavra por palavra: branca, sem traçado, 48 px, centralizada, com glow fixo e entrada suave."""
    cab = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,"
        "MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Padrao,Lato,{TAMANHO},{BRANCO},{BRANCO},{BRANCO},&HFF000000,-1,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    palavras = [p for f in corte.frases for p in f.palavras]
    linhas = []
    for k, w in enumerate(palavras):
        ini = w.ini - corte.ini
        fim = (palavras[k + 1].ini if k + 1 < len(palavras) else w.fim) - corte.ini
        fim = max(fim, ini + 0.05)
        mov = f"\\move({X},{Y - DESLOCAMENTO},{X},{Y},0,{ENTRADA_MS})"
        texto = w.texto.upper()
        # camada 0: glow fixo (halo branco desfocado); camada 1: texto nítido, sem traçado
        glow = (f"{{\\an5{mov}\\bord8\\blur10\\3c{BRANCO}\\1a&HFF&\\3a&HFF&"
                f"\\t(0,{ENTRADA_MS},\\1a&H80&\\3a&H80&)}}{texto}")
        nitido = (f"{{\\an5{mov}\\bord0\\shad0\\alpha&HFF&"
                  f"\\t(0,{ENTRADA_MS},\\alpha&H00&)}}{texto}")
        linhas.append(f"Dialogue: 0,{_t(ini)},{_t(fim)},Padrao,,0,0,0,,{glow}")
        linhas.append(f"Dialogue: 1,{_t(ini)},{_t(fim)},Padrao,,0,0,0,,{nitido}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho
