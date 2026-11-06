"""Orquestra as etapas do Garimpo. A pasta do projeto guarda tudo e permite retomar."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import cortes as mod_cortes
from . import exportar_md, legenda, midia, estrutura, transcricao
from .correcao import corretor
from .correcao.dicionario import Dicionario
from .modelos import Palavra


def _corrigir(palavras: list[Palavra], dic: Dicionario, pasta: Path, aceitar_todas: bool) -> list[Palavra]:
    """Etapas 3-5. Aplica variantes já conhecidas; as demais viram dúvidas para o usuário aprovar."""
    texto = " ".join(p.texto for p in palavras)
    sugestoes = corretor.sugerir(texto, dic)
    aplicar = [s for s in sugestoes if s.conhecida or aceitar_todas]
    duvidas = [s for s in sugestoes if s not in aplicar]
    linhas = ["# Dúvidas de escrita", ""]
    linhas += [f"- `{s.original}` -> `{s.sugestao}` (confiança {s.confianca:.0%})" for s in duvidas] or ["Nenhuma."]
    (pasta / "duvidas.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    if not aplicar:
        return palavras
    # corrige palavra a palavra preservando os tempos: o termo novo ocupa a 1ª palavra do trecho
    pos, inicios = 0, []
    for p in palavras:
        inicios.append(pos)
        pos += len(p.texto) + 1
    saida = list(palavras)
    for s in sorted(aplicar, key=lambda s: s.inicio, reverse=True):
        ids = [i for i, a in enumerate(inicios) if s.inicio <= a < s.fim]
        if not ids:
            continue
        primeira, ultima = saida[ids[0]], saida[ids[-1]]
        fim_txt = "".join(c for c in ultima.texto[-1:] if c in ".,;:!?…")
        saida[ids[0]:ids[-1] + 1] = [Palavra(s.sugestao + fim_txt, primeira.ini, ultima.fim,
                                             primeira.quadro_ini, ultima.quadro_fim)]
    return saida


def analisar(video: Path, pasta: Path, modelo: str, aceitar_todas: bool) -> list:
    pasta.mkdir(parents=True, exist_ok=True)
    info = midia.informacoes(video)
    fps = info["fps"]
    wav = pasta / "audio.wav"
    if not wav.exists():
        print("1/5 extraindo áudio...")
        midia.extrair_wav(video, wav)
    json_tr = pasta / "transcricao.json"
    if json_tr.exists():
        palavras, fps = transcricao.carregar(json_tr)
    else:
        print("2/5 transcrevendo (pode demorar em CPU)...")
        palavras = transcricao.transcrever(wav, fps, modelo)
        transcricao.salvar(palavras, json_tr, fps)
    print("3/5 corrigindo com o dicionário...")
    palavras = _corrigir(palavras, Dicionario.carregar(), pasta, aceitar_todas)
    exportar_md.transcricao(palavras, pasta / "transcricao.md")
    print("4/5 frases, parágrafos e temas...")
    fs = estrutura.frases(palavras)
    ps = estrutura.paragrafos(fs)
    ts = estrutura.temas(ps)
    cs = mod_cortes.sugerir(ts)
    exportar_md.frases(fs, pasta / "frases.md", fps)
    exportar_md.paragrafos(ps, pasta / "paragrafos.md", fps)
    exportar_md.temas(ts, pasta / "temas", cs, fps)
    exportar_md.cortes(cs, pasta / "cortes.md", fps)
    print("5/5 prévias em WAV...")
    for i, c in enumerate(cs, 1):
        midia.previa_wav(video, c.ini, c.fim, pasta / "previas" / f"corte-{i:02d}.wav")
    dados = [{"n": i, "tema": c.tema, "ini": c.ini, "fim": c.fim,
              "palavras": [vars(p) for f in c.frases for p in f.palavras]} for i, c in enumerate(cs, 1)]
    (pasta / "cortes.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    print(f"{len(ts)} temas, {len(cs)} cortes sugeridos. Veja {pasta / 'cortes.md'}")
    return cs


def exportar(video: Path, pasta: Path, aprovados: list[int]) -> None:
    from .modelos import Corte, Frase

    dados = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))
    for d in dados:
        if d["n"] not in aprovados:
            continue
        palavras = [Palavra(**p) for p in d["palavras"]]
        c = Corte(d["tema"], [Frase(palavras)], 0.0)
        ass = legenda.gerar_ass(c, pasta / "saida" / f"corte-{d['n']:02d}.ass")
        mp4 = midia.cortar_vertical(video, d["ini"], d["fim"], ass, pasta / "saida" / f"corte-{d['n']:02d}.mp4")
        print("gerado:", mp4)


def main() -> None:
    ap = argparse.ArgumentParser(prog="garimpo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analisar", help="vídeo -> transcrição, temas e cortes sugeridos")
    a.add_argument("video", type=Path)
    a.add_argument("--pasta", type=Path, required=True)
    a.add_argument("--modelo", default="small")
    a.add_argument("--aceitar-todas", action="store_true", help="aplica todas as correções sugeridas (teste)")
    e = sub.add_parser("exportar", help="corta e legenda os cortes aprovados")
    e.add_argument("video", type=Path)
    e.add_argument("--pasta", type=Path, required=True)
    e.add_argument("--aprovados", required=True, help="números separados por vírgula, ex.: 1,3")
    args = ap.parse_args()
    if args.cmd == "analisar":
        analisar(args.video, args.pasta, args.modelo, args.aceitar_todas)
    else:
        exportar(args.video, args.pasta, [int(x) for x in args.aprovados.split(",")])


if __name__ == "__main__":
    main()
