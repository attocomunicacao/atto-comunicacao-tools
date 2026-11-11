"""Motor de transições entre planos (referências em docs/pesquisa/2026-11-referencias-edicao.md).

- **flash cut**: na virada (gancho → corpo, ou troca de locutor) o vídeo "gagueja" entre o plano que sai (A) e o que
  entra (B) quadro a quadro, com quadros em que a pessoa vira uma **silhueta branca** sobre o fundo.
  Recorte da pessoa: interseção (mínimo, E lógico) de dois modelos MediaPipe Selfie Segmentation (ONNX, Apache-2.0) —
  o multiclasse (pessoa = cabelo+pele+rosto+roupa) e o binário; só fica branco o que os dois chamam de pessoa.
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

# lab ciclo 10: o modelo multiclasse separa pessoa (cabelo, pele, rosto, roupa) de objetos — o binário punha mesa e
# notebook dentro da silhueta. MediaPipe Selfie Multiclass 256x256 (Apache-2.0), conversão ONNX.
SEGMENTACAO = ("FreeHugsForRobots/ps-skin-seg", "selfie_multiclass_256x256.onnx")
# lab ciclo 30: interseção dos dois — o multiclasse confunde notebook com roupa (e mesa com pele), o binário confunde
# microfone com pessoa; o que só um deles vê não entra na silhueta.
SEGMENTACAO_BIN = ("onnx-community/mediapipe_selfie_segmentation", "onnx/model.onnx")
CLASSES_PESSOA = (1, 2, 3, 4)  # 0 fundo · 1 cabelo · 2 pele do corpo · 3 rosto · 4 roupa · 5 outros
FLASH_ANTES = 0.1    # s antes do corte (3 quadros a 30 fps)
FLASH_DEPOIS = 0.1   # s depois do corte
# Medido em videoplayback (2).mp4 (27,2-28,4 s, quadro a quadro): o 1º quadro é um borrão ampliado (~250%),
# em 0,3 s já está em ~140% e assenta em 100% perto de 1 s — "ease out" com a curva puxada, obturador 360°.
# v0.7 (retorno do cliente): 250% em 1 s com tmix ficou com "fantasmas" e lento demais. Agora é um punch-in
# curto e limpo: 145% → 100% em 0,45 s, ease-out exponencial, sem mistura de quadros.
ZOOM_INICIAL = 1.45  # escala no 1º quadro do plano que entra
ZOOM_DURACAO = 0.7   # s até assentar em 100% (lab ciclo 8: cauda mais longa, como a referência)

# Padrão QUADRO A QUADRO (v0.7, medido em videoplayback (1).mp4, 0,5-1,35 s a 24 fps): a silhueta branca pisca
# um quadro sim, um não; A = plano que sai, B = plano que entra, "w" = silhueta. Termina limpo em B.
# Cliente (teste real, 10/11): flash de 2 a 4 quadros, sem "vai e volta" — 1 quadro de silhueta antes do corte e
# 2 depois, sempre no plano do próprio instante.
PADRAO_ANTES = ["A", "A", "Aw"]
PADRAO_DEPOIS = ["Bw", "Bw", "B"]

_sessao = None
_sessao_bin = None


def _segmentador():
    global _sessao
    if _sessao is None:
        import onnxruntime as ort
        repo, arquivo = SEGMENTACAO
        modelo = recursos.pasta_cache() / "segmentacao" / "selfie_multiclass_256.onnx"
        recursos.baixar(repo, arquivo, modelo)
        _sessao = ort.InferenceSession(str(modelo), providers=["CPUExecutionProvider"])
    return _sessao


def _segmentador_bin():
    global _sessao_bin
    if _sessao_bin is None:
        import onnxruntime as ort
        repo, arquivo = SEGMENTACAO_BIN
        modelo = recursos.pasta_cache() / "segmentacao" / "mediapipe_selfie.onnx"
        recursos.baixar(repo, arquivo, modelo)
        _sessao_bin = ort.InferenceSession(str(modelo), providers=["CPUExecutionProvider"])
    return _sessao_bin


def _entrada_rgb(sessao, quadro: np.ndarray):
    """Prepara o quadro BGR para a sessão (NCHW ou NHWC, RGB/255 float32); devolve (nome da entrada, tensor)."""
    import cv2
    entrada = sessao.get_inputs()[0]
    forma = entrada.shape  # ex.: [1, 3, 256, 256] ou [1, 256, 256, 3]
    nchw = len(forma) == 4 and forma[1] == 3
    h_in = forma[2] if nchw else forma[1]
    w_in = forma[3] if nchw else forma[2]
    h_in = h_in if isinstance(h_in, int) else 256
    w_in = w_in if isinstance(w_in, int) else 256
    x = cv2.resize(cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB), (w_in, h_in)).astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None] if nchw else x[None]
    return entrada.name, x


def mascara_pessoa(quadro: np.ndarray) -> np.ndarray:
    """Máscara 0..1 da(s) pessoa(s) no quadro BGR (mesmo tamanho do quadro)."""
    import cv2
    s = _segmentador()
    nome, x = _entrada_rgb(s, quadro)
    y = np.squeeze(s.run(None, {nome: x})[0])
    if y.ndim == 3:  # multiclasse (H, W, 6): probabilidade de "pessoa" = soma das classes de pessoa (softmax)
        if y.shape[-1] != 6 and y.shape[0] == 6:
            y = np.moveaxis(y, 0, -1)
        e = np.exp(y - y.max(-1, keepdims=True))
        pr = e / e.sum(-1, keepdims=True) if (y.min() < 0 or y.max() > 1.001) else y
        y = pr[..., list(CLASSES_PESSOA)].sum(-1)
    # lab ciclo 30: interseção com o binário (mínimo) — tira notebook/mesa que o multiclasse chama de roupa/pele.
    sb = _segmentador_bin()
    nome_b, xb = _entrada_rgb(sb, quadro)
    yb = np.squeeze(sb.run(None, {nome_b: xb})[0])  # saída "alphas" [1, 1, 256, 256] → (256, 256), já 0..1
    if yb.ndim == 3:  # (H, W, 1) ou (H, W, 2): medido no modelo em cache, o canal 0 é a pessoa
        yb = yb[..., 0] if yb.shape[-1] in (1, 2) else yb[0]
    yb = cv2.resize(yb.astype(np.float32), (y.shape[1], y.shape[0]), interpolation=cv2.INTER_LINEAR)
    y = np.minimum(np.clip(y, 0, 1), np.clip(yb, 0, 1))  # mínimo = E lógico; a média geométrica deixava o microfone branco
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
            bloco = padrao[min(i, len(padrao) - 1)]
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
    return f"1+({ZOOM_INICIAL}-1)*pow(2,-7*{p})*(1-{p})"


def cadeia_zoom_entrada(fps: float) -> str:
    """Cadeia de filtros inteira do zoom de início de plano (entrada 1080x1920 → saída 1080x1920).

    Supersampling 2x antes do zoompan (enquadramento anda em meio pixel) e, depois dele, desfoque gaussiano só nos
    quadros 0 e 1 — o motion blur do punch-in, proporcional ao deslocamento daquele quadro, como na referência
    (videoplayback (2).mp4): o 1º quadro é um borrão, o 3º já é nítido. Sem tmix: a mistura de quadros do v0.7
    deixava fantasmas e o cliente rejeitou. A vírgula dentro de eq(n, 0) vai escapada com barra invertida porque
    a cadeia vive dentro de um filtergraph."""
    return (f"scale=2160:3840:flags=bicubic,"
            f"zoompan=z='{expr_zoom_entrada(fps)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={fps:g},"
            "gblur=sigma=2.4:enable='eq(n\\,0)',gblur=sigma=1.1:enable='eq(n\\,1)',"
            "setsar=1,format=yuv420p")
