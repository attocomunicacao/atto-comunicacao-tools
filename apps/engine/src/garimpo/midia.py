"""Operações de mídia com FFmpeg."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _rodar(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{args[0]} falhou: {r.stderr[-800:]}")


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


def cortar_vertical(video: Path, ini: float, fim: float, ass: Path | None, saida: Path) -> Path:
    """Etapas 10-11: corta o trecho em 1080x1920 (fundo desfocado + vídeo inteiro) e queima a legenda."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    # O fundo é desfocado em miniatura (1/10) e ampliado: visualmente igual (SSIM 0,994) e ~1,6x mais rápido.
    fundo = ("[0:v]scale=108:192:force_original_aspect_ratio=increase,crop=108:192,boxblur=3:2,"
             "scale=1080:1920:flags=bicubic[bg]")
    frente = "[0:v]scale=1080:-2[fg]"
    comp = "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    if ass is not None:
        comp += f",ass='{_caminho_filtro(ass)}'"
    filtro = f"{fundo};{frente};{comp}[v]"
    _rodar(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(video),
            "-filter_complex", filtro, "-map", "[v]", "-map", "0:a:0",
            "-c:v", "libx264", "-preset", "faster", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(saida)])
    return saida
