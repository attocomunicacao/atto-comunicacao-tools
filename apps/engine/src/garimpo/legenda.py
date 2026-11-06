"""Legenda dinâmica palavra por palavra (ASS), Lato em MAIÚSCULAS, 1080x1920."""
from __future__ import annotations

from pathlib import Path

from .modelos import Corte

DESTAQUE = "&H00C8E62E"  # #2ee6c8 da ATTO (ASS usa BGR)
BRANCO = "&H00FFFFFF"


def _t(s: float) -> str:
    s = max(s, 0.0)
    h, resto = divmod(s, 3600)
    m, seg = divmod(resto, 60)
    return f"{int(h)}:{int(m):02d}:{seg:05.2f}"


def gerar_ass(corte: Corte, caminho: Path, palavras_por_bloco: int = 3) -> Path:
    cab = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,"
        "MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Padrao,Lato,84,{BRANCO},{BRANCO},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,520,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    palavras = [p for f in corte.frases for p in f.palavras]
    linhas = []
    for b in range(0, len(palavras), palavras_por_bloco):
        bloco = palavras[b:b + palavras_por_bloco]
        for k, atual in enumerate(bloco):
            ini = atual.ini - corte.ini
            fim = (bloco[k + 1].ini if k + 1 < len(bloco) else atual.fim) - corte.ini
            texto = " ".join(
                (f"{{\\c{DESTAQUE}}}{w.texto.upper()}{{\\c{BRANCO}}}" if w is atual else w.texto.upper())
                for w in bloco)
            linhas.append(f"Dialogue: 0,{_t(ini)},{_t(max(fim, ini + 0.05))},Padrao,,0,0,0,,{texto}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho
