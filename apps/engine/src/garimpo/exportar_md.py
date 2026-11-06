"""Gera os arquivos .md (transcrição, frases, parágrafos, um por tema, cortes)."""
from __future__ import annotations

from pathlib import Path

from .modelos import Corte, Frase, Paragrafo, Palavra, Tema


def tc(seg: float, fps: float) -> str:
    h, r = divmod(int(seg), 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d} (quadro {round(seg * fps)})"


def transcricao(palavras: list[Palavra], destino: Path) -> None:
    destino.write_text("# Transcrição\n\n" + " ".join(p.texto for p in palavras) + "\n", encoding="utf-8")


def frases(fs: list[Frase], destino: Path, fps: float) -> None:
    linhas = ["# Frases", ""]
    linhas += [f"- `{tc(f.ini, fps)}` {f.texto}" for f in fs]
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def paragrafos(ps: list[Paragrafo], destino: Path, fps: float) -> None:
    linhas = ["# Parágrafos", ""]
    for i, p in enumerate(ps, 1):
        linhas += [f"## Parágrafo {i} · `{tc(p.ini, fps)}` a `{tc(p.fim, fps)}`", "", p.texto, ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")


def temas(ts: list[Tema], pasta: Path, cortes: list[Corte], fps: float) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(ts, 1):
        linhas = [f"# Tema {i:02d}: {t.titulo}", "",
                  f"- Início: `{tc(t.ini, fps)}`", f"- Fim: `{tc(t.fim, fps)}`",
                  f"- Palavras-chave: {', '.join(t.palavras_chave)}", ""]
        deste = [c for c in cortes if t.ini <= c.ini and c.fim <= t.fim]
        for c in deste:
            linhas += ["## Trecho mais relevante", "",
                       f"`{tc(c.ini, fps)}` a `{tc(c.fim, fps)}` · {c.duracao:.0f} s", "", c.texto, ""]
        if not deste:
            linhas += ["_Tema curto demais para um corte de 30 s._", ""]
        linhas += ["## Texto completo", ""] + [p.texto + "\n" for p in t.paragrafos]
        (pasta / f"tema-{i:02d}.md").write_text("\n".join(linhas), encoding="utf-8")


def cortes(cs: list[Corte], destino: Path, fps: float) -> None:
    linhas = ["# Cortes sugeridos", "", "Ouça as prévias em `previas/` e aprove os números desejados.", ""]
    for i, c in enumerate(cs, 1):
        linhas += [f"## Corte {i:02d} · {c.duracao:.0f} s · {c.tema}", "",
                   f"`{tc(c.ini, fps)}` a `{tc(c.fim, fps)}`", "", c.texto, ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")
