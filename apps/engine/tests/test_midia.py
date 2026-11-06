import subprocess

from garimpo import midia


def _video_de_teste(destino):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(destino)], check=True)
    return destino


def test_informacoes_e_extrair_wav(tmp_path):
    v = _video_de_teste(tmp_path / "v.mp4")
    info = midia.informacoes(v)
    assert (info["largura"], info["altura"]) == (1920, 1080) and round(info["fps"]) == 30
    wav = midia.extrair_wav(v, tmp_path / "a.wav")
    assert wav.stat().st_size > 10_000


def test_corte_vertical_1080x1920(tmp_path):
    v = _video_de_teste(tmp_path / "v.mp4")
    saida = midia.cortar_vertical(v, 0.5, 2.5, None, tmp_path / "c.mp4")
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", str(saida)], capture_output=True, text=True)
    assert r.stdout.strip() == "1080,1920"
