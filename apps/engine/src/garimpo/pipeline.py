"""Orquestra as etapas do Garimpo. A pasta do projeto guarda tudo e permite retomar.

Fluxo do app: `transcrever` (etapas 1-2 e dúvidas) -> usuário aprova -> `estruturar` (etapas 3-9)
-> usuário aprova cortes -> `exportar` (etapas 10-11). `analisar` junta as duas primeiras para a linha de comando.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    print("PCT 0", flush=True)


def _log(texto: str) -> None:
    """Linha de detalhe para a tela de carregamento do app (aba "Ver detalhes")."""
    print(f"LOG {texto}", flush=True)


def _pct(f: float) -> None:
    print(f"PCT {max(0, min(100, round(f * 100)))}", flush=True)


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


def transcrever(video: Path, pasta: Path, modelo: str, refazer: bool = False) -> None:
    """Etapas 1-2 e levantamento das dúvidas de escrita (etapa 3).

    A transcrição fica no cache global por conteúdo (`cache.py`): o mesmo vídeo, em qualquer projeto novo, não é
    transcrito de novo. `refazer` (botão "Transcrever de novo") ignora o cache."""
    from . import cache
    pasta.mkdir(parents=True, exist_ok=True)
    info = midia.informacoes(video)
    fps = info["fps"]
    _log(f"Vídeo: {video.name} ({info['largura']}x{info['altura']} a {fps:.2f} fps)")
    wav = pasta / "audio.wav"
    if not wav.exists():
        _etapa(1, 3, "Extraindo o áudio")
        _log("FFmpeg: extraindo o áudio em WAV mono 16 kHz")
        midia.extrair_wav(video, wav)
        _log(f"Áudio extraído ({wav.stat().st_size / 1e6:.0f} MB)")
    json_tr = pasta / "transcricao.json"
    termos = list(Dicionario.carregar().termos.keys())
    k = cache.chave_transcricao(video, modelo, termos)
    guardada = None if refazer else cache.ler_json("transcricoes", k)
    if guardada and not json_tr.exists():
        _etapa(2, 3, "Transcrição reaproveitada")
        json_tr.write_text(json.dumps(guardada, ensure_ascii=False), encoding="utf-8")
        _log(f"Transcrição reaproveitada do cache ({len(guardada['palavras'])} palavras): este vídeo já foi transcrito")
        print("CACHE transcricao", flush=True)
        _pct(1)
    if refazer and json_tr.exists():
        json_tr.unlink()
    if not json_tr.exists():
        _etapa(2, 3, "Transcrevendo (pode demorar em CPU)")
        _log(f"Whisper '{modelo}' no processador (int8, beam 5), idioma pt, tempo por palavra")
        ultimo = [-10.0]

        def progresso(f: float, t: float, total: float, texto: str) -> None:
            _pct(f)
            if t - ultimo[0] >= 20:   # um detalhe a cada ~20 s de áudio
                ultimo[0] = t
                _log(f"{int(t // 60)}:{int(t % 60):02d} de {int(total // 60)}:{int(total % 60):02d}  “{texto[:90]}”")

        if termos:
            _log(f"Termos do seu dicionário como dica para o Whisper: {', '.join(termos[:12])}")
        palavras = transcricao.transcrever(wav, fps, modelo, progresso, hotwords=termos, log=_log)
        transcricao.salvar(palavras, json_tr, fps)
        cache.gravar_json("transcricoes", k, json.loads(json_tr.read_text(encoding="utf-8")))
        _log(f"Transcrição pronta: {len(palavras)} palavras (guardada no cache para os próximos testes)")
    palavras, fps = _carregar_palavras(pasta)
    _etapa(3, 3, "Procurando dúvidas de escrita")
    texto = " ".join(p.texto for p in palavras)
    _log("Comparando com o seu dicionário (som e escrita)")
    sugestoes = corretor.sugerir(texto, Dicionario.carregar())
    _log(f"{len(sugestoes)} dúvida(s) de escrita encontrada(s)")
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


def estruturar(video: Path, pasta: Path, aprovadas: list[int], descricao: str = "") -> list[Corte]:
    """Etapas 4-9: aplica as correções aprovadas, aprende com elas e gera .md, temas, cortes e prévias.

    `descricao`: o que o usuário escreveu sobre o vídeo (tema, público, objetivo); guia a relevância dos cortes."""
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
    _log(f"Aplicando {len(escolhidas)} correção(ões) aprovada(s); o dicionário aprendeu as novas")
    palavras = _aplicar(palavras, escolhidas)
    exportar_md.transcricao(palavras, pasta / "transcricao.md")
    _etapa(2, 3, "Separando frases, parágrafos e temas")
    from . import semantica
    emb = semantica.carregar(_log)
    fs, ps, ts, vs = estrutura.estruturar(palavras, emb, _log)
    _log(f"{len(fs)} frases, {len(ps)} parágrafos, {len(ts)} temas"
         + (" (pausas + sentido)" if vs is not None else " (pausas + vocabulário)"))
    if descricao.strip():
        (pasta / "descricao.txt").write_text(descricao, encoding="utf-8")
        _log(f"Descrição do vídeo como guia: “{descricao.strip()[:100]}”")
    _log("Pontuando trechos: gancho, fechamento sem cortar a fala, contexto, relevância e coesão")
    from . import juiz as mod_juiz
    juiz = mod_juiz.carregar(_log)
    ordem = {id(f): i for i, f in enumerate(fs)}
    todas_t = [f for t in ts for f in t.frases]
    vs_t = vs[[ordem[id(f)] for f in todas_t]] if vs is not None else None
    cs = mod_cortes.sugerir(ts, juiz=juiz, log=_log, descricao=descricao, vs=vs_t)
    _log(f"{len(cs)} corte(s) escolhido(s)")
    exportar_md.frases(fs, pasta / "frases.md", fps)
    exportar_md.paragrafos(ps, pasta / "paragrafos.md", fps)
    exportar_md.temas(ts, pasta / "temas", cs, fps)
    exportar_md.cortes(cs, pasta / "cortes.md", fps)
    _etapa(3, 3, "Ajustando os limites e gerando prévias de áudio")
    wav = None
    try:
        wav = mod_cortes.carregar_wav(pasta / "audio.wav")
    except Exception as e:  # sem o áudio de trabalho, usa só a folga fixa
        _log(f"Sem análise de silêncio ({e}); usando folga fixa")
    dados = []
    for i, c in enumerate(cs, 1):
        ant = next((p.fim for p in reversed(palavras) if p.fim <= c.ini - 0.001), None)
        prox = next((p.ini for p in palavras if p.ini >= c.fim + 0.001), None)
        ini, fim = mod_cortes.ajustar_limites(c.ini, c.fim, ant, prox, wav)
        _log(f"Corte {i:02d}: {c.ini:.2f}s-{c.fim:.2f}s  ->  {ini:.2f}s-{fim:.2f}s (silêncio mais próximo); abre com “{c.texto[:60]}…”")
        midia.previa_wav(video, ini, fim, pasta / "previas" / f"corte-{i:02d}.wav")
        _pct(i / len(cs))
        item = {"n": i, "tema": c.tema, "ini": ini, "fim": fim, "duracao": fim - ini, "texto": c.texto,
                "palavras": [vars(p) for f in c.frases for p in f.palavras]}
        if c.teaser is not None:
            t_ant = next((p.fim for p in reversed(palavras) if p.fim <= c.teaser.ini - 0.001), None)
            t_prox = next((p.ini for p in palavras if p.ini >= c.teaser.fim + 0.001), None)
            ti, tf = mod_cortes.ajustar_limites(c.teaser.ini, c.teaser.fim, t_ant, t_prox, wav)
            item["teaser"] = {"ini": ti, "fim": tf, "texto": c.teaser.texto, "palavras": [vars(p) for p in c.teaser.palavras]}
            item["duracao"] += tf - ti
            item["texto"] = f"[gancho] {c.teaser.texto} … {c.texto}"
            _log(f"  Corte {i:02d} abre com o gancho “{c.teaser.texto[:60]}”")
        dados.append(item)
    (pasta / "cortes.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    print(f"RESULTADO {len(ts)} temas {len(cs)} cortes", flush=True)
    return cs


def analisar(video: Path, pasta: Path, modelo: str, aceitar_todas: bool, descricao: str = "",
             refazer: bool = False) -> None:
    transcrever(video, pasta, modelo, refazer)
    itens = json.loads((pasta / "duvidas.json").read_text(encoding="utf-8"))
    estruturar(video, pasta, [d["id"] for d in itens] if aceitar_todas else [], descricao)


def transicoes_da_montagem(arquivos: list[Path], flashes: list[list[float]], tmp: Path, nome: str, log) -> list:
    """Peças da montagem com os flash cuts encaixados: na virada gancho → corpo e nas trocas de locutor marcadas
    como "flash". Cada flash substitui FLASH_ANTES s antes e FLASH_DEPOIS s depois do corte (duração igual)."""
    from . import transicoes as tr
    fps = midia.informacoes(arquivos[0])["fps"]
    pecas: list = []
    inicio = 0.0  # de onde o arquivo atual continua (depois de um flash na virada anterior)
    k = 0

    def flash(arq_a, ta, arq_b, tb):
        nonlocal k
        k += 1
        try:
            return tr.flash_cut(arq_a, ta, arq_b, tb, tmp / f"{nome}-flash{k}.mkv", fps, log)
        except Exception as e:
            log(f"Flash cut indisponível ({str(e)[:80]}); corte seco")
            return None

    for i, arq in enumerate(arquivos):
        dur = midia.duracao(arq)
        for t in sorted(flashes[i]):  # trocas de locutor dentro do trecho
            if t - tr.FLASH_ANTES > inicio + 0.2 and t + tr.FLASH_DEPOIS < dur - 0.2:
                clipe = flash(arq, t, arq, t)
                if clipe:
                    pecas += [(arq, inicio, t - tr.FLASH_ANTES), (clipe, None, None)]
                    inicio = t + tr.FLASH_DEPOIS
        proximo = arquivos[i + 1] if i + 1 < len(arquivos) else None
        if proximo is not None and dur - tr.FLASH_ANTES > inicio + 0.2:
            clipe = flash(arq, dur, proximo, 0.0)  # virada gancho -> corpo
            if clipe:
                pecas += [(arq, inicio, dur - tr.FLASH_ANTES), (clipe, None, None)]
                inicio = tr.FLASH_DEPOIS
                continue
        pecas.append((arq, inicio, None))
        inicio = 0.0
    return pecas


def exportar(video: Path, pasta: Path, aprovados: list[int], logo: Path | None = None) -> None:
    """Etapas 10-11: edição dinâmica de cada corte aprovado.

    1. plano de motion (legenda, ilustrações, zooms, transição do gancho) — `motion.planejar`;
    2. trechos em 1080x1920 reenquadrados com zooms suaves — `midia.trecho_vertical`;
    3. montagem (gancho + corpo), áudio masterizado (-14 LUFS) e logo final — `midia.montar`;
    4. camada ATTO Motion renderizada quadro a quadro pelo app — `midia.aplicar_motion`
       (sem o app, na linha de comando, a legenda ASS é queimada no lugar)."""
    from . import juiz as mod_juiz
    from . import motion
    dados = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))
    escolhidos = [d for d in dados if d["n"] in aprovados]
    if logo is not None and not logo.exists():
        _log(f"Logo não encontrada ({logo}); gerando sem ela")
        logo = None
    _log("Logo no final de cada corte: " + (logo.name if logo else "nenhuma"))
    tem_motion = midia.comando_motion() is not None
    _log("Camada de motion: " + ("ATTO Motion (GSAP, quadro a quadro)" if tem_motion else "indisponível; legenda ASS"))
    llm = None
    if tem_motion:
        j = mod_juiz.carregar(_log)
        llm = j.llm if j else None
    saida_dir = pasta / "saida"
    tmp = saida_dir / "tmp"
    manter = os.environ.get("ATTO_MANTER_TMP") == "1"
    for k, d in enumerate(escolhidos, 1):
        nome = f"corte-{d['n']:02d}"
        _etapa(k, len(escolhidos), f"Gerando o corte {d['n']:02d}")
        partes = []
        if d.get("teaser"):
            t = d["teaser"]
            partes.append((t["ini"], t["fim"], [Palavra(**p) for p in t["palavras"]]))
        partes.append((d["ini"], d["fim"], [Palavra(**p) for p in d["palavras"]]))
        _log(f"Corte {d['n']:02d}: {len(partes)} trecho(s), {sum(b - a for a, b, _ in partes):.0f} s"
             + (" (abre com gancho)" if len(partes) > 1 else ""))
        plano = motion.planejar(partes, llm, _log)
        arquivos, deslocamento, flashes = [], 0.0, []
        for j, (a, b, _) in enumerate(partes):
            zooms = [z - deslocamento for z in plano.zooms if deslocamento <= z < deslocamento + (b - a) - 2]
            # cache por conteúdo: reeditar só a animação não refaz o reenquadramento (ATTO_MANTER_TMP=1)
            chave = hashlib.sha1(json.dumps([video.name, a, b, zooms, j == 0, "v4"]).encode()).hexdigest()[:10]
            arq = tmp / f"{nome}-{j}-{chave}.mkv"
            cache_flash = arq.with_suffix(".flash.json")
            if not (manter and arq.exists() and cache_flash.exists()):
                internos: list[float] = []
                midia.trecho_vertical(video, a, b, arq, zooms, _log, lambda f, j=j: _pct(0.45 * (j + f) / len(partes)),
                                      cortes_flash=internos, zoom_inicio=(j == 0))  # todo corte abre com zoom in
                cache_flash.write_text(json.dumps(internos), encoding="utf-8")
            else:
                _log(f"Trecho {j + 1} reaproveitado do cache")
            flashes.append(json.loads(cache_flash.read_text(encoding="utf-8")))
            arquivos.append(arq)
            deslocamento += b - a
        pecas = transicoes_da_montagem(arquivos, flashes, tmp, nome, _log)
        from . import sons as mod_sons
        faixa = mod_sons.faixa(mod_sons.eventos(plano.cenas, plano.transicoes))
        base, dur = midia.montar(pecas, tmp / f"{nome}-base.mp4", logo, _log, faixa)
        _pct(0.5)
        mp4 = saida_dir / f"{nome}.mp4"
        if tem_motion:
            from . import espaco
            try:
                espaco.aplicar(espaco.mapear(base, log=_log), plano.grupos, plano.cenas, _log)
            except Exception as e:  # sem mapa: zonas padrão
                _log(f"Mapa de espaço indisponível ({str(e)[:80]})")
                espaco.aplicar(None, plano.grupos, plano.cenas)
            job = {"fps": 30, "duracao": round(dur, 3), "largura": 1080, "altura": 1920, "palavras": plano.palavras,
                   "grupos": plano.grupos, "cenas": plano.cenas, "transicoes": plano.transicoes}
            fps = midia.informacoes(base)["fps"]
            job["fps"] = round(fps, 3)
            (saida_dir / f"{nome}.plano.json").write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
            midia.aplicar_motion(base, job, mp4, _log, lambda f: _pct(0.5 + 0.5 * f))
        else:
            c = Corte(d["tema"], [Frase([Palavra(**p) for p in d["palavras"]])], 0.0)
            ass = legenda.gerar_ass(c, saida_dir / f"{nome}.ass", origem=d["ini"] - (deslocamento - (d["fim"] - d["ini"])))
            midia.queimar_legenda(base, ass, mp4)
        if not manter:
            for arq in arquivos + [base]:
                arq.unlink(missing_ok=True)
        _log(f"Arquivo pronto: {mp4.name} ({mp4.stat().st_size / 1e6:.0f} MB)")
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

    t = com_video("transcrever", "etapas 1-2 e dúvidas de escrita")
    t.add_argument("--modelo", default=transcricao.MODELO_PADRAO)
    t.add_argument("--refazer", action="store_true", help="ignora a transcrição guardada no cache")
    es = com_video("estruturar", "etapas 4-9")
    es.add_argument("--aprovadas", default="", help="ids de dúvidas, ex.: 0,2")
    es.add_argument("--descricao", default="", help="tema, público e objetivo do vídeo (guia a escolha)")
    a = com_video("analisar", "tudo até os cortes sugeridos")
    a.add_argument("--modelo", default=transcricao.MODELO_PADRAO)
    a.add_argument("--aceitar-todas", action="store_true")
    a.add_argument("--descricao", default="")
    a.add_argument("--refazer", action="store_true")
    e = com_video("exportar", "corta e legenda os aprovados")
    e.add_argument("--aprovados", required=True)
    e.add_argument("--logo", type=Path, default=None, help="imagem para o fim de cada corte")
    d = sub.add_parser("dicionario", help="gerencia o dicionário pessoal")
    d.add_argument("acao", choices=["listar", "adicionar", "remover"])
    d.add_argument("termo", nargs="?")

    args = ap.parse_args()
    ids = lambda s: [int(x) for x in s.split(",") if x.strip()]  # noqa: E731
    if args.cmd == "transcrever":
        transcrever(args.video, args.pasta, args.modelo, args.refazer)
    elif args.cmd == "estruturar":
        estruturar(args.video, args.pasta, ids(args.aprovadas), args.descricao)
    elif args.cmd == "analisar":
        analisar(args.video, args.pasta, args.modelo, args.aceitar_todas, args.descricao, args.refazer)
    elif args.cmd == "exportar":
        exportar(args.video, args.pasta, ids(args.aprovados), args.logo)
    else:
        dicionario(args.acao, args.termo)


if __name__ == "__main__":
    main()
