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
