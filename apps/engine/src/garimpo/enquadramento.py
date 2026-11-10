"""Enquadramento vertical inteligente: o vídeo original ocupa 100% da tela 1080x1920.

- Um rosto em quadro (ou um falante ativo entre vários): recorte 9:16 de altura total centrado nele.
- Dois rostos em quadro (câmera central): tela dividida ao meio, exatos 960 px para cada pessoa;
  a da esquerda em cima e a da direita embaixo.

A análise amostra o vídeo em poucos quadros por segundo, detecta rostos (YuNet, ONNX incluído) e
gera segmentos de enquadramento FIXO: o eixo só muda quando a câmera ou o falante mudam de verdade
(nada de acompanhar o tremor da detecção). Entre dois segmentos há uma dissolução suave.
"""
from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

LARG, ALT = 1080, 1920
METADE = ALT // 2
FPS_AMOSTRA = 4          # quadros analisados por segundo
MIN_AMOSTRAS = 8         # uma mudança precisa durar ~2 s para valer
JANELA_MODO = 9          # filtro de maioria do modo (único/dividido) para ignorar piscadas da detecção
ZONA_MORTA = 0.45        # fração da largura do recorte que o rosto pode andar sem mexer no eixo
TRANSICAO_S = 0.4        # dissolução entre enquadramentos
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


def _filtrar_modos(cheias: list[tuple[str, list[float]]]) -> list[tuple[str, list[float]]]:
    """Maioria do modo numa janela: um rosto que some/aparece por 1-2 amostras não troca o layout."""
    meio = JANELA_MODO // 2
    saida = []
    for i, dec in enumerate(cheias):
        ini, fim = max(0, i - meio), min(len(cheias), i + meio + 1)
        modo = Counter(d[0] for d in cheias[ini:fim]).most_common(1)[0][0]
        if dec[0] != modo:
            # pega a decisão vizinha mais próxima que já está no modo vencedor
            viz = sorted((j for j in range(ini, fim) if cheias[j][0] == modo), key=lambda j: abs(j - i))
            dec = cheias[viz[0]]
        saida.append(dec)
    return saida


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
    cheias = _filtrar_modos(cheias)

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
            if len(janela) >= min(MIN_AMOSTRAS, len(cheias) - i) and len(janela) == MIN_AMOSTRAS \
                    and all(perto(j, cheias[i]) for j in janela):
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
    return _unir_mesmo_eixo(saida, cw)


def _unir_mesmo_eixo(segs: list[Segmento], cw: float) -> list[Segmento]:
    """Segmentos vizinhos com o mesmo layout e eixo quase igual viram um só (sem corte à toa)."""
    saida = [segs[0]]
    for s in segs[1:]:
        a = saida[-1]
        if a.modo == s.modo and len(a.centros) == len(s.centros) \
                and all(abs(x - y) <= ZONA_MORTA * cw for x, y in zip(a.centros, s.centros)):
            a.fim = s.fim
        else:
            saida.append(s)
    return saida


# ---------------------------------------------------------------- leitura do vídeo e detecção

def _quadros(video: Path, ini: float, fim: float, largura: int, altura: int):
    """Entrega quadros reduzidos (largura 640) à taxa FPS_AMOSTRA."""
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


def analisar(video: Path, ini: float, fim: float, largura: int, altura: int, log=None) -> list[Segmento]:
    """Detecta rostos no trecho e devolve os segmentos de enquadramento."""
    import cv2
    # O modelo entra por buffer: o OpenCV não abre arquivos em caminhos com acento (ex.: "Comunicação").
    modelo = np.frombuffer(_MODELO.read_bytes(), np.uint8)
    detector = cv2.FaceDetectorYN.create("onnx", modelo, np.empty(0, np.uint8), (640, 360), 0.6, 0.3, 5000)
    amostras: list[tuple[str, list[float]]] = []
    ant = None
    sem_rosto = 0
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
        sem_rosto += not rostos
        amostras.append(_escolher(rostos, largura))
        ant = quadro
    segs = segmentar(amostras, fim - ini, largura, altura)
    if log:
        log(f"Enquadramento: {len(amostras)} amostras, {sem_rosto} sem rosto, {len(segs)} segmento(s)")
        for s in segs:
            pos = " e ".join(f"x={c:.0f}" for c in s.centros) or "centro"
            log(f"  {s.ini:5.1f}s a {s.fim:5.1f}s  {'tela dividida' if s.modo == 'dividido' else 'recorte único'}  ({pos})")
    return segs


# ---------------------------------------------------------------- filtro ffmpeg

def _layout(s: Segmento, i: int, cw_u: int, cw_m: int, largura: int, altura: int, fps: float, ate: float) -> str:
    corte = f"trim=start={s.ini:.3f}:end={ate:.3f},setpts=PTS-STARTPTS,fps={fps:g}"
    if s.modo == "dividido" and len(s.centros) == 2:
        xa, xb = (_limite(c, cw_m, largura) for c in s.centros)
        return (f"[0:v]{corte},split=2[a{i}][b{i}];"
                f"[a{i}]crop={cw_m}:{altura}:{xa}:0,scale={LARG}:{METADE},setsar=1[t{i}];"
                f"[b{i}]crop={cw_m}:{altura}:{xb}:0,scale={LARG}:{METADE},setsar=1[u{i}];"
                f"[t{i}][u{i}]vstack=inputs=2,setsar=1,format=yuv420p[s{i}]")
    x = _limite(s.centros[0] if s.centros else largura / 2, cw_u, largura)
    return f"[0:v]{corte},crop={cw_u}:{altura}:{x}:0,scale={LARG}:{ALT},setsar=1,format=yuv420p[s{i}]"


def estilos_troca(n_segmentos: int) -> list[str]:
    """Estilo de cada troca de enquadramento/locutor. v0.7 (pedido do cliente): TODA troca é flash cut
    (videoplayback (1).mp4); o zoom in fica para o início de cada corte (`filtro(..., zoom_inicio=True)`)."""
    return ["flash" for _ in range(max(n_segmentos - 1, 0))]


def filtro(segmentos: list[Segmento], largura: int, altura: int, fps: float = 30.0,
           estilos: list[str] | None = None, zoom_inicio: bool = False) -> str:
    """Monta o trecho do filter_complex que produz [cv] (1080x1920) a partir de [0:v].

    Com `estilos` (um por troca): "zoom" = o plano que entra começa ampliado e com desfoque de movimento e assenta
    (transicoes.expr_zoom_entrada); "flash" = corte seco aqui, e o flash cut é encaixado depois na montagem.
    `zoom_inicio`: o 1º plano do trecho entra com o zoom in (início de todo corte, videoplayback (2).mp4).
    Sem `estilos`: dissolução (xfade), comportamento antigo. A duração total nunca muda."""
    cw_u, cw_m = geometria(largura, altura)
    if estilos is not None and (len(segmentos) > 1 or zoom_inicio):
        from .transicoes import ZOOM_DURACAO, expr_zoom_entrada
        partes = [_layout(s, i, cw_u, cw_m, largura, altura, fps, s.fim) for i, s in enumerate(segmentos)]
        rotulos = []
        for i in range(len(segmentos)):
            com_zoom = (i == 0 and zoom_inicio) or (i > 0 and estilos[i - 1] == "zoom")
            if com_zoom and segmentos[i].fim - segmentos[i].ini > ZOOM_DURACAO + 0.3:
                d = ZOOM_DURACAO
                partes.append(
                    f"[s{i}]split=2[h{i}][r{i}];"
                    f"[h{i}]trim=end={d:.3f},setpts=PTS-STARTPTS,scale=2160:3840:flags=bicubic,"
                    f"zoompan=z='{expr_zoom_entrada(fps)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={LARG}x{ALT}:fps={fps:g},"
                    f"setsar=1,format=yuv420p[hz{i}];"
                    f"[r{i}]trim=start={d:.3f},setpts=PTS-STARTPTS[rr{i}];"
                    f"[hz{i}][rr{i}]concat=n=2:v=1:a=0[z{i}]")
                rotulos.append(f"[z{i}]")
            else:
                rotulos.append(f"[s{i}]")
        if len(rotulos) == 1:
            partes.append(f"{rotulos[0]}null[cv]")
        else:
            partes.append(f"{''.join(rotulos)}concat=n={len(rotulos)}:v=1:a=0[cv]")
        return ";".join(partes)
    n = len(segmentos)
    d = TRANSICAO_S
    if n > 1:
        d = min(d, min(s.fim - s.ini for s in segmentos) / 3)
    partes = []
    for i, s in enumerate(segmentos):
        ate = s.fim + (d if i < n - 1 else 0)
        partes.append(_layout(s, i, cw_u, cw_m, largura, altura, fps, ate))
    if n == 1:
        partes.append("[s0]null[cv]")
    else:
        atual = "s0"
        for i in range(1, n):
            saida = "cv" if i == n - 1 else f"x{i}"
            partes.append(f"[{atual}][s{i}]xfade=transition=fade:duration={d:.3f}:offset={segmentos[i].ini:.3f}[{saida}]")
            atual = saida
    return ";".join(partes)
