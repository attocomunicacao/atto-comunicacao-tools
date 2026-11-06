"""Orquestra as etapas do Garimpo. A pasta do projeto guarda tudo e permite retomar.

Fluxo do app: `transcrever` (etapas 1-2 e dúvidas) -> usuário aprova -> `estruturar` (etapas 3-9)
-> usuário aprova cortes -> `exportar` (etapas 10-11). `analisar` junta as duas primeiras para a linha de comando.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cortes as mod_cortes
from . import estrutura, exportar_md, legenda, midia, transcricao
from .correcao import corretor
from .correcao.corretor import Sugestao
from .correcao.dicionario import Dicionario
from .modelos import Corte, Frase, Palavra


def _etapa(n: int, total: int, texto: str) -> None:
    print(f"ETAPA {n}/{total} {texto}", flush=True)


def _aplicar(palavras: list[Palavra], escolhidas: list[Sugestao]) -> list[Palavra]:
    """Aplica as correções preservando os tempos: o termo novo ocupa o intervalo das palavras trocadas."""
    if not escolhidas:
        return palavras
    pos, inicios = 0, []
    for p in palavras:
        inicios.append(pos)
        pos += len(p.texto) + 1
    saida = list(palavras)
    for s in sorted(escolhidas, key=lambda s: s.inicio, reverse=True):
        ids = [i for i, a in enumerate(inicios) if s.inicio <= a < s.fim]
        if not ids:
            continue
        primeira, ultima = saida[ids[0]], saida[ids[-1]]
        pontuacao = "".join(c for c in ultima.texto[-1:] if c in ".,;:!?…")
        saida[ids[0]:ids[-1] + 1] = [Palavra(s.sugestao + pontuacao, primeira.ini, ultima.fim,
                                             primeira.quadro_ini, ultima.quadro_fim)]
    return saida


def _carregar_palavras(pasta: Path) -> tuple[list[Palavra], float]:
    return transcricao.carregar(pasta / "transcricao.json")


def transcrever(video: Path, pasta: Path, modelo: str) -> None:
    """Etapas 1-2 e levantamento das dúvidas de escrita (etapa 3)."""
    pasta.mkdir(parents=True, exist_ok=True)
    fps = midia.informacoes(video)["fps"]
    wav = pasta / "audio.wav"
    if not wav.exists():
        _etapa(1, 3, "Extraindo o áudio")
        midia.extrair_wav(video, wav)
    json_tr = pasta / "transcricao.json"
    if not json_tr.exists():
        _etapa(2, 3, "Transcrevendo (pode demorar em CPU)")
        palavras = transcricao.transcrever(wav, fps, modelo)
        transcricao.salvar(palavras, json_tr, fps)
    palavras, fps = _carregar_palavras(pasta)
    _etapa(3, 3, "Procurando dúvidas de escrita")
    texto = " ".join(p.texto for p in palavras)
    sugestoes = corretor.sugerir(texto, Dicionario.carregar())
    itens = []
    for i, s in enumerate(sugestoes):
        itens.append({"id": i, "original": s.original, "sugestao": s.sugestao, "confianca": s.confianca,
                      "conhecida": s.conhecida, "inicio": s.inicio, "fim": s.fim,
                      "contexto": texto[max(0, s.inicio - 70):s.fim + 70]})
    (pasta / "duvidas.json").write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    lin = ["# Dúvidas de escrita", ""] + (
        [f"- `{d['original']}` -> `{d['sugestao']}` ({d['confianca']:.0%})" for d in itens] or ["Nenhuma."])
    (pasta / "duvidas.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
    print(f"RESULTADO {len(itens)} duvidas", flush=True)


def estruturar(video: Path, pasta: Path, aprovadas: list[int]) -> list[Corte]:
    """Etapas 4-9: aplica as correções aprovadas, aprende com elas e gera .md, temas, cortes e prévias."""
    palavras, fps = _carregar_palavras(pasta)
    itens = json.loads((pasta / "duvidas.json").read_text(encoding="utf-8"))
    dic = Dicionario.carregar()
    escolhidas = []
    for d in itens:
        if d["conhecida"] or d["id"] in aprovadas:
            escolhidas.append(Sugestao(d["inicio"], d["fim"], d["original"], d["sugestao"], d["confianca"], d["conhecida"]))
            if not d["conhecida"]:
                dic.aprender(d["original"], d["sugestao"])
    dic.salvar()
    _etapa(1, 3, "Corrigindo a transcrição")
    palavras = _aplicar(palavras, escolhidas)
    exportar_md.transcricao(palavras, pasta / "transcricao.md")
    _etapa(2, 3, "Separando frases, parágrafos e temas")
    fs = estrutura.frases(palavras)
    ps = estrutura.paragrafos(fs)
    ts = estrutura.temas(ps)
    cs = mod_cortes.sugerir(ts)
    exportar_md.frases(fs, pasta / "frases.md", fps)
    exportar_md.paragrafos(ps, pasta / "paragrafos.md", fps)
    exportar_md.temas(ts, pasta / "temas", cs, fps)
    exportar_md.cortes(cs, pasta / "cortes.md", fps)
    _etapa(3, 3, "Gerando prévias de áudio")
    for i, c in enumerate(cs, 1):
        midia.previa_wav(video, c.ini, c.fim, pasta / "previas" / f"corte-{i:02d}.wav")
    dados = [{"n": i, "tema": c.tema, "ini": c.ini, "fim": c.fim, "duracao": c.duracao, "texto": c.texto,
              "palavras": [vars(p) for f in c.frases for p in f.palavras]} for i, c in enumerate(cs, 1)]
    (pasta / "cortes.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    print(f"RESULTADO {len(ts)} temas {len(cs)} cortes", flush=True)
    return cs


def analisar(video: Path, pasta: Path, modelo: str, aceitar_todas: bool) -> None:
    transcrever(video, pasta, modelo)
    itens = json.loads((pasta / "duvidas.json").read_text(encoding="utf-8"))
    estruturar(video, pasta, [d["id"] for d in itens] if aceitar_todas else [])


def exportar(video: Path, pasta: Path, aprovados: list[int]) -> None:
    dados = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))
    escolhidos = [d for d in dados if d["n"] in aprovados]
    for k, d in enumerate(escolhidos, 1):
        _etapa(k, len(escolhidos), f"Gerando o corte {d['n']:02d}")
        c = Corte(d["tema"], [Frase([Palavra(**p) for p in d["palavras"]])], 0.0)
        ass = legenda.gerar_ass(c, pasta / "saida" / f"corte-{d['n']:02d}.ass")
        mp4 = midia.cortar_vertical(video, d["ini"], d["fim"], ass, pasta / "saida" / f"corte-{d['n']:02d}.mp4")
        print(f"ARQUIVO {mp4}", flush=True)


def dicionario(acao: str, termo: str | None) -> None:
    dic = Dicionario.carregar()
    if acao == "adicionar" and termo:
        dic.adicionar_termo(termo.strip())
        dic.salvar()
    elif acao == "remover" and termo:
        dic.remover_termo(termo)
        dic.salvar()
    print("DICIONARIO " + json.dumps(dic.termos, ensure_ascii=False), flush=True)


def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="garimpo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def com_video(nome: str, ajuda: str):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("video", type=Path)
        p.add_argument("--pasta", type=Path, required=True)
        return p

    com_video("transcrever", "etapas 1-2 e dúvidas de escrita").add_argument("--modelo", default="small")
    com_video("estruturar", "etapas 4-9").add_argument("--aprovadas", default="", help="ids de dúvidas, ex.: 0,2")
    a = com_video("analisar", "tudo até os cortes sugeridos")
    a.add_argument("--modelo", default="small")
    a.add_argument("--aceitar-todas", action="store_true")
    com_video("exportar", "corta e legenda os aprovados").add_argument("--aprovados", required=True)
    d = sub.add_parser("dicionario", help="gerencia o dicionário pessoal")
    d.add_argument("acao", choices=["listar", "adicionar", "remover"])
    d.add_argument("termo", nargs="?")

    args = ap.parse_args()
    ids = lambda s: [int(x) for x in s.split(",") if x.strip()]  # noqa: E731
    if args.cmd == "transcrever":
        transcrever(args.video, args.pasta, args.modelo)
    elif args.cmd == "estruturar":
        estruturar(args.video, args.pasta, ids(args.aprovadas))
    elif args.cmd == "analisar":
        analisar(args.video, args.pasta, args.modelo, args.aceitar_todas)
    elif args.cmd == "exportar":
        exportar(args.video, args.pasta, ids(args.aprovados))
    else:
        dicionario(args.acao, args.termo)


if __name__ == "__main__":
    main()
