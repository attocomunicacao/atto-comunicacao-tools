"""Enquadramento vertical inteligente: o vídeo original ocupa 100% da tela 1080x1920.

- Um rosto em quadro (ou um falante ativo entre vários): recorte 9:16 de altura total centrado nele.
- Dois ou mais rostos em quadro (câmera central): tela dividida ao meio, exatos 960 px para cada
  pessoa; a da esquerda em cima e a da direita embaixo.

A análise amostra o vídeo em poucos quadros por segundo, detecta rostos (YuNet, ONNX incluído) e
gera segmentos de enquadramento fixo, sem tremida: troca só quando a mudança dura de verdade.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

LARG, ALT = 1080, 1920
METADE = ALT // 2
FPS_AMOSTRA = 4          # quadros analisados por segundo
MIN_AMOSTRAS = 3         # uma mudança precisa durar ~0,75 s para valer
ZONA_MORTA = 0.12        # fração da largura do recorte tolerada antes de re-centralizar
_MODELO = Path(__file__).parent / "dados" / "yunet.onnx"


@dataclass
class Rosto:
    cx: float   # centro, em px do vídeo original
    cy: float
    larg: float
    alt: float
    movimento: float = 0.0  # movimento da boca (maior = mais fala)


@dataclass
class Segmento:
    ini: float                     # segundos, relativos ao início do corte
    fim: float
    modo: str                      # "unico" ou "dividido"
    centros: list[float] = field(default_factory=list)  # x do(s) rosto(s); em "dividido": [cima, baixo]


def _limite(x: float, cw: float, largura: int) -> int:
    """Posição x do recorte (largura cw) centrado em x, sem sair do vídeo; par para o ffmpeg."""
    return int(round(min(max(x - cw / 2, 0), largura - cw) / 2) * 2)


def geometria(largura: int, altura: int) -> tuple[int, int]:
    """Larguras de recorte (do original) para o modo único (9:16) e para cada metade (9:8)."""
    unico = min(largura, int(altura * LARG / ALT) // 2 * 2)
    metade = min(largura, int(altura * LARG / METADE) // 2 * 2)
    return unico, metade


# ---------------------------------------------------------------- escolha do enquadramento por amostra

def _escolher(rostos: list[Rosto], largura: int) -> tuple[str, list[float]]:
    """Decide o enquadramento de uma amostra. Retorna (modo, centros)."""
    if not rostos:
        return "unico", []
    maior = max(r.larg for r in rostos)
    rostos = sorted((r for r in rostos if r.larg >= 0.5 * maior), key=lambda r: r.cx)  # ignora rostos ao fundo
    if len(rostos) == 1:
        return "unico", [rostos[0].cx]
    if len(rostos) == 2:
        return "dividido", [rostos[0].cx, rostos[1].cx]
    # três ou mais (painel): fica só com quem está falando
    falando = max(rostos, key=lambda r: r.movimento)
    return "unico", [falando.cx]


def segmentar(amostras: list[tuple[str, list[float]]], duracao: float, largura: int, altura: int,
              fps: float = FPS_AMOSTRA) -> list[Segmento]:
    """Transforma a sequência de decisões por amostra em segmentos de enquadramento estável."""
    if not amostras:
        return [Segmento(0.0, duracao, "unico", [largura / 2])]
    cw, _ = geometria(largura, altura)

    # preenche amostras sem rosto com a última decisão conhecida (ou a primeira conhecida)
    ultimo = next((a for a in amostras if a[1]), ("unico", [largura / 2]))
    cheias = []
    for modo, cs in amostras:
        if cs:
            ultimo = (modo, cs)
        cheias.append(ultimo)

    def perto(a, b):
        """Mesma configuração (modo e nº de rostos) e posições dentro da zona morta."""
        return (a[0] == b[0] and len(a[1]) == len(b[1])
                and all(abs(x - y) <= ZONA_MORTA * cw for x, y in zip(a[1], b[1])))

    segs: list[list] = []   # [indice_inicial, decisao_ancora, [decisoes]]
    i = 0
    while i < len(cheias):
        if not segs:
            segs.append([i, cheias[i], [cheias[i]]])
            i += 1
        elif perto(cheias[i], segs[-1][1]):
            segs[-1][2].append(cheias[i])
            i += 1
        else:
            # candidato a mudança: só vale se se mantiver por MIN_AMOSTRAS amostras seguidas
            janela = cheias[i:i + MIN_AMOSTRAS]
            if len(janela) == MIN_AMOSTRAS and all(perto(j, cheias[i]) for j in janela):
                segs.append([i, cheias[i], list(janela)])
                i += MIN_AMOSTRAS
            else:
                segs[-1][2].append(segs[-1][1])  # ruído: segura o enquadramento atual
                i += 1

    saida = []
    for k, (ini_i, _, decs) in enumerate(segs):
        ini = ini_i / fps
        fim = (segs[k + 1][0] / fps) if k + 1 < len(segs) else duracao
        modo = decs[0][0]
        n = len(decs[0][1])
        centros = [float(np.median([d[1][j] for d in decs if d[0] == modo and len(d[1]) == n])) for j in range(n)]
        saida.append(Segmento(0.0 if k == 0 else ini, fim, modo, centros))
    return saida


# ---------------------------------------------------------------- leitura do vídeo e detecção

def _quadros(video: Path, ini: float, fim: float, largura: int, altura: int):
    """Entrega quadros em cinza reduzidos (largura 640) à taxa FPS_AMOSTRA."""
    w = 640
    h = int(round(altura * w / largura / 2) * 2)
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(video), "-an",
         "-vf", f"fps={FPS_AMOSTRA},scale={w}:{h}", "-pix_fmt", "bgr24", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * 3
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3), w / largura
    finally:
        p.stdout.close()
        p.wait()


def _movimento_boca(anterior: np.ndarray, atual: np.ndarray, r: Rosto, escala: float) -> float:
    x0, x1 = int((r.cx - r.larg / 2) * escala), int((r.cx + r.larg / 2) * escala)
    y0, y1 = int((r.cy + r.alt * 0.1) * escala), int((r.cy + r.alt / 2) * escala)  # metade de baixo do rosto
    a = anterior[max(y0, 0):y1, max(x0, 0):x1]
    b = atual[max(y0, 0):y1, max(x0, 0):x1]
    if a.size == 0 or a.shape != b.shape:
        return 0.0
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def analisar(video: Path, ini: float, fim: float, largura: int, altura: int) -> list[Segmento]:
    """Detecta rostos no trecho e devolve os segmentos de enquadramento."""
    import cv2
    # O modelo entra por buffer: o OpenCV não abre arquivos em caminhos com acento (ex.: "Comunicação").
    modelo = np.frombuffer(_MODELO.read_bytes(), np.uint8)
    detector = cv2.FaceDetectorYN.create("onnx", modelo, np.empty(0, np.uint8), (640, 360), 0.6, 0.3, 5000)
    amostras: list[tuple[str, list[float]]] = []
    ant = None
    for quadro, escala in _quadros(video, ini, fim, largura, altura):
        h, w = quadro.shape[:2]
        detector.setInputSize((w, h))
        _, achados = detector.detect(quadro)
        rostos = []
        for f in (achados if achados is not None else []):
            x, y, fw, fh = (float(v) / escala for v in f[:4])
            r = Rosto(x + fw / 2, y + fh / 2, fw, fh)
            if ant is not None:
                r.movimento = _movimento_boca(ant, quadro, r, escala)
            rostos.append(r)
        amostras.append(_escolher(rostos, largura))
        ant = quadro
    return segmentar(amostras, fim - ini, largura, altura)


# ---------------------------------------------------------------- filtro ffmpeg

def filtro(segmentos: list[Segmento], largura: int, altura: int) -> str:
    """Monta o trecho do filter_complex que produz [cv] (1080x1920) a partir de [0:v]."""
    cw_u, cw_m = geometria(largura, altura)
    partes, saidas = [], []
    for i, s in enumerate(segmentos):
        corte = f"trim=start={s.ini:.3f}:end={s.fim:.3f},setpts=PTS-STARTPTS"
        if s.modo == "dividido" and len(s.centros) == 2:
            xa, xb = (_limite(c, cw_m, largura) for c in s.centros)
            partes.append(
                f"[0:v]{corte},split=2[a{i}][b{i}];"
                f"[a{i}]crop={cw_m}:{altura}:{xa}:0,scale={LARG}:{METADE}[t{i}];"
                f"[b{i}]crop={cw_m}:{altura}:{xb}:0,scale={LARG}:{METADE}[u{i}];"
                f"[t{i}][u{i}]vstack=inputs=2[s{i}]")
        else:
            x = _limite(s.centros[0] if s.centros else largura / 2, cw_u, largura)
            partes.append(f"[0:v]{corte},crop={cw_u}:{altura}:{x}:0,scale={LARG}:{ALT}[s{i}]")
        saidas.append(f"[s{i}]")
    if len(saidas) == 1:
        partes.append(f"{saidas[0]}null[cv]")
    else:
        partes.append(f"{''.join(saidas)}concat=n={len(saidas)}:v=1:a=0[cv]")
    return ";".join(partes)
