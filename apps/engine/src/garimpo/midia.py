"""Operações de mídia com FFmpeg."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def _rodar(args: list[str], aoProgresso=None, duracao: float = 0.0) -> None:
    """Roda um comando; com `aoProgresso(fracao)` acompanha o `-progress` do ffmpeg."""
    if aoProgresso is None:
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{args[0]} falhou: {r.stderr[-800:]}")
        return
    with tempfile.TemporaryFile("w+", encoding="utf-8") as erro:
        p = subprocess.Popen(args + ["-progress", "pipe:1", "-nostats"], stdout=subprocess.PIPE, stderr=erro,
                             text=True, encoding="utf-8")
        for linha in p.stdout:
            if linha.startswith("out_time_us=") and duracao > 0:
                try:
                    aoProgresso(min(int(linha.split("=")[1]) / 1e6 / duracao, 1.0))
                except ValueError:
                    pass
        p.wait()
        if p.returncode != 0:
            erro.seek(0)
            raise RuntimeError(f"{args[0]} falhou: {erro.read()[-800:]}")


def informacoes(video: Path) -> dict:
    """Devolve largura, altura e fps do primeiro vídeo."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate", "-of", "json", str(video)],
        check=True, capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return {"largura": s["width"], "altura": s["height"], "fps": int(n) / int(d)}


def extrair_wav(video: Path, saida: Path) -> Path:
    """Etapa 1: qualquer vídeo (mp4, mov, mts...) -> WAV mono 16 kHz."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    _rodar(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(saida)])
    return saida


def previa_wav(video: Path, ini: float, fim: float, saida: Path) -> Path:
    """Etapa 9: trecho em WAV para o usuário ouvir antes de aprovar."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    _rodar(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(video),
            "-vn", "-ac", "1", "-ar", "22050", str(saida)])
    return saida


def _caminho_filtro(p: Path) -> str:
    """Caminho no formato aceito pelo filtro `ass` do FFmpeg no Windows."""
    return p.resolve().as_posix().replace(":", r"\:")


LOGO_S = 2.2          # duração do cartão final com a logo
LOGO_LARGURA = 520    # px na tela de 1080


def _filtro_logo(dur: float) -> str:
    """Cartão final: o último quadro congela, escurece suavemente e a logo sobe com fade (ease-out)."""
    t0 = f"{dur:.3f}"
    return (
        f"[1:v]scale={LOGO_LARGURA}:-2,format=rgba,fade=in:st=0:d=0.6:alpha=1,setpts=PTS+{t0}/TB[lg];"
        f"color=c=black:s=1080x1920:r=30:d={LOGO_S},format=rgba,fade=in:st=0:d=0.5:alpha=1,"
        f"colorchannelmixer=aa=0.62,setpts=PTS+{t0}/TB[dim];"
        f"[vv]tpad=stop_mode=clone:stop_duration={LOGO_S}[vp];"
        f"[vp][dim]overlay=eof_action=pass[vd];"
        f"[vd][lg]overlay=x=(W-w)/2:y='(H-h)/2+70*pow(1-min(1,max(0,(t-{t0})/0.8)),3)':eof_action=pass[v]")


def cortar_vertical(video: Path, ini: float, fim: float, ass: Path | None, saida: Path,
                    logo: Path | None = None, log=None, aoProgresso=None) -> Path:
    """Etapas 10-11: corta o trecho em 1080x1920 com o vídeo original ocupando a tela toda.

    O enquadramento segue o falante (ver `enquadramento`); com dois rostos em quadro a tela é dividida
    ao meio, com dissolução entre os layouts. Queima a legenda e, se houver, acrescenta a logo no fim."""
    from . import enquadramento
    saida.parent.mkdir(parents=True, exist_ok=True)
    info = informacoes(video)
    dur = fim - ini
    segmentos = enquadramento.analisar(video, ini, fim, info["largura"], info["altura"], log)
    comp = enquadramento.filtro(segmentos, info["largura"], info["altura"], round(info["fps"], 3))
    if ass is not None:
        fontes = os.environ.get("ATTO_FONTES")  # empacotado: a Lato vem junto, sem depender do Windows
        extra = f":fontsdir='{_caminho_filtro(Path(fontes))}'" if fontes else ""
        comp += f";[cv]ass='{_caminho_filtro(ass)}'{extra}[vv]"
    else:
        comp += ";[cv]null[vv]"
    # fade curto no áudio (sem estalo no começo/fim)
    audio = f"[0:a:0]afade=t=in:st=0:d=0.04,afade=t=out:st={max(dur - 0.08, 0):.3f}:d=0.08"
    entradas = ["-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(video)]
    total, ultimo = dur, "[vv]"
    if logo is not None:
        comp += ";" + _filtro_logo(dur)
        entradas += ["-loop", "1", "-t", f"{LOGO_S:.3f}", "-i", str(logo)]
        audio += f",apad=pad_dur={LOGO_S}"
        total, ultimo = dur + LOGO_S, "[v]"
    comp += f";{audio}[a]"
    if log:
        log(f"Codificando {total:.1f}s em 1080x1920 (H.264 CRF 16)" + (" + logo final" if logo else ""))
    _rodar(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", comp, "-map", ultimo, "-map", "[a]",
            "-c:v", "libx264", "-preset", "faster", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(saida)],
           aoProgresso, total)
    return saida


# ---------------------------------------------------------------- edição dinâmica (v0.5)

ZOOM = 0.09            # punch-in de 9% nos momentos de ênfase
ZOOM_ENTRADA, ZOOM_SEGURA, ZOOM_SAIDA = 0.55, 1.8, 0.8
# Masterização de voz para redes: corta grave de ruído, compressão leve e loudness de -14 LUFS (padrão de Reels/TikTok/YouTube).
MASTER_AUDIO = ("highpass=f=75,acompressor=threshold=-21dB:ratio=3:attack=8:release=160:makeup=2,"
                "loudnorm=I=-14:TP=-1.5:LRA=9")


def _expr_zoom(zooms: list[float], fps: float) -> str:
    """Expressão do zoompan: soma de "sinos" suaves (smoothstep na entrada e na saída) nos instantes de ênfase."""
    if not zooms:
        return "1"
    partes = []
    for k, z in enumerate(zooms):
        a, b = 2 * k, 2 * k + 1
        sobe = f"(st({a},clip((on/{fps:g}-{z:.3f})/{ZOOM_ENTRADA},0,1))*0+ld({a})*ld({a})*(3-2*ld({a})))"
        desce = f"(1-(st({b},clip((on/{fps:g}-{z + ZOOM_ENTRADA + ZOOM_SEGURA:.3f})/{ZOOM_SAIDA},0,1))*0+ld({b})*ld({b})*(3-2*ld({b}))))"
        partes.append(f"{sobe}*{desce}")
    return f"1+{ZOOM}*min(1,{'+'.join(partes)})"


def trecho_vertical(video: Path, ini: float, fim: float, saida: Path, zooms: list[float] | None = None,
                    log=None, aoProgresso=None, cortes_flash: list[float] | None = None) -> Path:
    """Um trecho do vídeo em 1080x1920: reenquadrado (rosto/tela dividida), com zooms suaves de ênfase.

    Intermediário de alta qualidade (CRF 12); a legenda, as ilustrações e a logo entram depois."""
    from . import enquadramento
    saida.parent.mkdir(parents=True, exist_ok=True)
    info = informacoes(video)
    fps = round(info["fps"], 3)
    dur = fim - ini
    segmentos = enquadramento.analisar(video, ini, fim, info["largura"], info["altura"], log)
    estilos = enquadramento.estilos_troca(len(segmentos))
    comp = enquadramento.filtro(segmentos, info["largura"], info["altura"], fps, estilos)
    if cortes_flash is not None:
        # trocas em flash cut: o clipe de transição é encaixado na montagem (instantes locais do trecho)
        cortes_flash += [segmentos[k + 1].ini for k, e in enumerate(estilos) if e == "flash"]
    if log and len(segmentos) > 1:
        log("Trocas de enquadramento/locutor: " + ", ".join(f"{segmentos[k + 1].ini:.1f}s {e}" for k, e in enumerate(estilos)))
    if zooms:
        # supersampling 2x antes do zoompan: o enquadramento anda em meio pixel, sem tremor
        comp += (f";[cv]scale=2160:3840:flags=bicubic,zoompan=z='{_expr_zoom(zooms, fps)}':"
                 f"x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)':d=1:s=1080x1920:fps={fps:g}[vz]")
        ultimo = "[vz]"
    else:
        ultimo = "[cv]"
    comp += f";[0:a:0]afade=t=in:st=0:d=0.03,afade=t=out:st={max(dur - 0.06, 0):.3f}:d=0.06[a]"
    _rodar(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(video),
            "-filter_complex", comp, "-map", ultimo, "-map", "[a]", "-c:v", "libx264", "-preset", "faster", "-crf", "12",
            "-pix_fmt", "yuv420p", "-r", f"{fps:g}", "-c:a", "pcm_s16le", "-t", f"{dur:.3f}", str(saida)], aoProgresso, dur)
    return saida


def duracao(arq: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def montar(trechos: list, saida: Path, logo: Path | None = None, log=None,
           sons: list[tuple[float, Path, float]] | None = None) -> tuple[Path, float]:
    """Junta as peças (ex.: gancho + flash cut + corpo), masteriza o áudio e acrescenta o cartão final da logo.

    Cada peça é um arquivo ou (arquivo, início, fim) — o recorte permite encaixar o clipe do flash cut no lugar
    exato. Retorna (arquivo, duração do conteúdo sem a logo)."""
    pecas = [(t, None, None) if isinstance(t, Path) else t for t in trechos]
    entradas: list[str] = []
    dur = 0.0
    filtros = []
    for k, (arq, a, b) in enumerate(pecas):
        entradas += ["-i", str(arq)]
        total_arq = duracao(arq)
        a = 0.0 if a is None else max(a, 0.0)
        b = total_arq if b is None else min(b, total_arq)
        dur += b - a
        filtros.append(f"[{k}:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[pv{k}];"
                       f"[{k}:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS[pa{k}]")
    n = len(pecas)
    comp = ";".join(filtros) + ";" + "".join(f"[pv{k}][pa{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vv][a0]"
    ultimo = "[vv]"
    audio = f"[a0]{MASTER_AUDIO}"
    total = dur
    if logo is not None:
        entradas += ["-loop", "1", "-t", f"{LOGO_S:.3f}", "-i", str(logo)]
        comp += ";" + _filtro_logo(dur).replace("[1:v]", f"[{n}:v]")
        audio += f",apad=pad_dur={LOGO_S}"
        ultimo, total = "[v]", dur + LOGO_S
    comp += f";{audio},aresample=48000[voz]"
    # design de som: cada efeito entra no seu instante, bem abaixo da voz já masterizada
    sons = sons or []
    base_idx = n + (1 if logo is not None else 0)
    for k, (t, arq, vol) in enumerate(sons):
        entradas += ["-i", str(arq)]
        ms = int(t * 1000)
        comp += f";[{base_idx + k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol}dB,adelay={ms}|{ms}[s{k}]"
    if sons:
        rotulos = "".join(f"[s{k}]" for k in range(len(sons)))
        comp += f";[voz]{rotulos}amix=inputs={len(sons) + 1}:duration=first:normalize=0,alimiter=limit=0.89[a]"
    else:
        comp += ";[voz]anull[a]"
    if log:
        log(f"Montando {n} trecho(s), {dur:.1f}s; áudio masterizado a -14 LUFS" + (" + logo final" if logo else "")
            + (f"; {len(sons)} efeito(s) sonoro(s)" if sons else ""))
    _rodar(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", comp, "-map", ultimo, "-map", "[a]",
            "-c:v", "libx264", "-preset", "faster", "-crf", "13", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.3f}", str(saida)])
    return saida, dur


def comando_motion() -> list[str] | None:
    """Como chamar o renderizador de motion (o app define ATTO_MOTION_CMD); None na linha de comando pura."""
    import json as _json
    bruto = os.environ.get("ATTO_MOTION_CMD")
    return _json.loads(bruto) if bruto else None


def aplicar_motion(base: Path, job: dict, saida: Path, log=None, aoProgresso=None) -> Path:
    """Sobrepõe a camada ATTO Motion (legenda + ilustrações) ao vídeo-base, renderizada pelo app quadro a quadro."""
    import json as _json
    cmd = comando_motion()
    if not cmd:
        raise RuntimeError("Renderizador de motion indisponível (ATTO_MOTION_CMD não definido)")
    job = {**job, "base": str(base), "saida": str(saida)}
    fontes = os.environ.get("ATTO_FONTES")
    if fontes:
        job["fontes"] = fontes
    arq = saida.with_suffix(".motion.json")
    arq.write_text(_json.dumps(job, ensure_ascii=False), encoding="utf-8")
    if log:
        log(f"Renderizando motion: {len(job['palavras'])} palavras, {len(job['cenas'])} ilustração(ões), quadro a quadro")
    p = subprocess.Popen([*cmd, str(arq)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                         encoding="utf-8", errors="replace")
    ultima = ""
    for linha in p.stdout:
        linha = linha.strip()
        if linha.startswith("PCT ") and aoProgresso:
            aoProgresso(int(linha[4:]) / 100)
        elif linha:
            ultima = linha
    p.wait()
    if p.returncode != 0 or not saida.exists() or ultima.startswith("ERRO"):
        raise RuntimeError(f"Render de motion falhou: {ultima}")
    return saida


def queimar_legenda(base: Path, ass: Path, saida: Path) -> Path:
    """Plano B sem o app (linha de comando): legenda ASS queimada sobre o vídeo-base."""
    fontes = os.environ.get("ATTO_FONTES")
    extra = f":fontsdir='{_caminho_filtro(Path(fontes))}'" if fontes else ""
    _rodar(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-vf", f"ass='{_caminho_filtro(ass)}'{extra}",
            "-c:v", "libx264", "-preset", "faster", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy",
            "-movflags", "+faststart", str(saida)])
    return saida
