"""Motor de transições entre planos (referências em docs/pesquisa/2026-11-referencias-edicao.md).

- **flash cut**: na virada (gancho → corpo, ou troca de locutor) o vídeo "gagueja" entre o plano que sai (A) e o que
  entra (B) em blocos de 2 quadros, com quadros em que a pessoa vira uma **silhueta branca** sobre o fundo.
  Recorte da pessoa: MediaPipe Selfie Segmentation (ONNX, Apache-2.0).
- **zoom**: o plano que entra começa ampliado (~230%) e com desfoque de movimento e assenta em 100% com
  desaceleração forte (curva de velocidade "ease out" + obturador 360°). Feito no filtro do trecho
  (`enquadramento.filtro`, `expr_zoom_entrada`).

A duração total nunca muda: o flash cut substitui quadros em volta do corte e usa o áudio original da mesma janela.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from . import recursos

SEGMENTACAO = ("onnx-community/mediapipe_selfie_segmentation", "onnx/model.onnx")
FLASH_ANTES = 0.4    # s antes do corte
FLASH_DEPOIS = 0.4   # s depois do corte
# Medido em videoplayback (2).mp4 (27,2-28,4 s, quadro a quadro): o 1º quadro é um borrão ampliado (~250%),
# em 0,3 s já está em ~140% e assenta em 100% perto de 1 s — "ease out" com a curva puxada, obturador 360°.
ZOOM_INICIAL = 2.5   # escala no 1º quadro do plano que entra
ZOOM_DURACAO = 1.0   # s até assentar em 100%

# Padrão em blocos de 2 quadros (lido quadro a quadro na referência): A = plano que sai, B = plano que entra,
# "w" = silhueta branca. Antes do corte domina A, depois domina B; termina limpo em B.
PADRAO_ANTES = ["A", "Aw", "A", "Bw", "A", "Aw"]
PADRAO_DEPOIS = ["B", "Bw", "A", "Bw", "B", "B"]

_sessao = None


def _segmentador():
    global _sessao
    if _sessao is None:
        import onnxruntime as ort
        repo, arquivo = SEGMENTACAO
        modelo = recursos.pasta_cache() / "segmentacao" / "mediapipe_selfie.onnx"
        recursos.baixar(repo, arquivo, modelo)
        _sessao = ort.InferenceSession(str(modelo), providers=["CPUExecutionProvider"])
    return _sessao


def mascara_pessoa(quadro: np.ndarray) -> np.ndarray:
    """Máscara 0..1 da(s) pessoa(s) no quadro BGR (mesmo tamanho do quadro)."""
    import cv2
    s = _segmentador()
    entrada = s.get_inputs()[0]
    forma = entrada.shape  # ex.: [1, 3, 256, 256] ou [1, 256, 256, 3]
    nchw = len(forma) == 4 and forma[1] == 3
    h_in = forma[2] if nchw else forma[1]
    w_in = forma[3] if nchw else forma[2]
    h_in = h_in if isinstance(h_in, int) else 256
    w_in = w_in if isinstance(w_in, int) else 256
    x = cv2.resize(cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB), (w_in, h_in)).astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None] if nchw else x[None]
    y = np.squeeze(s.run(None, {entrada.name: x})[0])
    if y.ndim == 3:  # canais: pega o de "pessoa" (último) se vier mais de um
        y = y[..., -1] if y.shape[-1] <= 4 else y[-1]
    m = cv2.resize(y.astype(np.float32), (quadro.shape[1], quadro.shape[0]), interpolation=cv2.INTER_LINEAR)
    m = np.clip((m - 0.35) / 0.3, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 2.5)


def silhueta(quadro: np.ndarray) -> np.ndarray:
    """A pessoa vira branca (com leve brilho na borda); o fundo fica como está."""
    import cv2
    m = mascara_pessoa(quadro)
    brilho = cv2.GaussianBlur(m, (0, 0), 14) * 0.35
    alfa = np.clip(m + brilho, 0, 1)[..., None]
    return (quadro * (1 - alfa) + 255 * alfa).astype(np.uint8)


def _quadros(arq: Path, ini: float, dur: float, w: int = 1080, h: int = 1920) -> list[np.ndarray]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(ini, 0):.3f}", "-i", str(arq), "-t", f"{dur:.3f}",
                        "-an", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True)
    n = w * h * 3
    return [np.frombuffer(r.stdout[i:i + n], np.uint8).reshape(h, w, 3) for i in range(0, len(r.stdout) - n + 1, n)]


def flash_cut(arq_a: Path, corte_a: float, arq_b: Path, corte_b: float, saida: Path, fps: float, log=None) -> Path:
    """Clipe de FLASH_ANTES+FLASH_DEPOIS s que substitui [corte_a-FLASH_ANTES, corte_a] de A e [corte_b, corte_b+FLASH_DEPOIS] de B.

    O áudio é o original dessas mesmas janelas (sem desvio de sincronia)."""
    a = _quadros(arq_a, corte_a - FLASH_ANTES, FLASH_ANTES)
    b = _quadros(arq_b, corte_b, FLASH_DEPOIS)
    if not a or not b:
        raise RuntimeError("flash cut: sem quadros nas janelas")
    cache_sil: dict[tuple[str, int], np.ndarray] = {}

    def pega(lado: str, i: int, branco: bool) -> np.ndarray:
        fonte = a if lado == "A" else b
        q = fonte[min(i, len(fonte) - 1)]
        if not branco:
            return q
        chave = (lado, min(i, len(fonte) - 1))
        if chave not in cache_sil:
            cache_sil[chave] = silhueta(q)
        return cache_sil[chave]

    saida_q: list[np.ndarray] = []
    for janela, padrao, lado_natural in ((a, PADRAO_ANTES, "A"), (b, PADRAO_DEPOIS, "B")):
        for i in range(len(janela)):
            bloco = padrao[min(i // 2, len(padrao) - 1)]
            lado, branco = bloco[0], bloco.endswith("w")
            # o lado "natural" usa o quadro do mesmo instante; o outro lado usa os primeiros/últimos quadros dele
            idx = i if lado == lado_natural else (i if lado == "B" else len(a) - len(janela) + i)
            saida_q.append(pega(lado, max(idx, 0), branco))
    saida.parent.mkdir(parents=True, exist_ok=True)
    h, w = saida_q[0].shape[:2]
    dur_v = len(saida_q) / fps
    # vídeo pela entrada padrão + áudio original das duas janelas
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-framerate", f"{fps:g}",
         "-i", "pipe:0",
         "-ss", f"{corte_a - FLASH_ANTES:.3f}", "-t", f"{FLASH_ANTES:.3f}", "-i", str(arq_a),
         "-ss", f"{corte_b:.3f}", "-t", f"{FLASH_DEPOIS:.3f}", "-i", str(arq_b),
         "-filter_complex", "[1:a][2:a]concat=n=2:v=0:a=1[a]", "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "faster", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le",
         "-t", f"{dur_v:.3f}", str(saida)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for q in saida_q:
        p.stdin.write(q.tobytes())
    p.stdin.close()
    erro = p.stderr.read().decode("utf-8", "replace")
    if p.wait() != 0:
        raise RuntimeError(f"flash cut falhou: {erro[-400:]}")
    if log:
        log(f"Transição flash cut: {len(saida_q)} quadros ({len(cache_sil)} silhuetas)")
    return saida


def expr_zoom_entrada(fps: float) -> str:
    """Escala do zoompan para o início de um plano: ZOOM_INICIAL → 1 em ZOOM_DURACAO s (ease-out exponencial)."""
    p = f"min(1,on/{fps:g}/{ZOOM_DURACAO})"
    return f"1+({ZOOM_INICIAL}-1)*pow(2,-10*{p})*(1-{p})"
