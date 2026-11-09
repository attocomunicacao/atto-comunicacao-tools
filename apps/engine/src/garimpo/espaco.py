"""Mapa de espaço da tela 1080x1920: onde estão os rostos ao longo do corte e quais zonas ficam livres.

Regra do cliente: ícones, textos e animações NUNCA ocupam o rosto do locutor. O motor detecta os rostos no vídeo
já montado (YuNet, 4 quadros/s), e cada legenda/ilustração recebe uma zona livre durante todo o tempo em que aparece.

Zonas candidatas (x, y, largura, altura) — escolhidas na ordem de preferência de cada tipo de elemento:
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

W, H = 1080, 1920
ZONAS: dict[str, tuple[int, int, int, int]] = {
    "base": (60, 1300, 960, 420),     # terço inferior (preferida da legenda)
    "topo": (60, 150, 960, 520),      # faixa de cima
    "centro": (60, 760, 960, 460),    # meio da tela (quando o rosto está em cima ou embaixo)
    "esquerda": (40, 420, 470, 900),  # lateral esquerda
    "direita": (570, 420, 470, 900),  # lateral direita
    "meio": (60, 880, 960, 160),      # costura da tela dividida (faixa fina entre os dois rostos)
}
PREFERENCIA = {
    "legenda": ["base", "meio", "centro", "topo"],
    "cena": ["topo", "centro", "esquerda", "direita", "base"],
    "cheia": [],  # tela cheia (imagem, citação): não precisa de zona
}
MARGEM = 0.18  # folga em volta do rosto (fração do tamanho do rosto)


@dataclass
class MapaRostos:
    tempos: list[float]
    caixas: list[list[tuple[float, float, float, float]]]  # por amostra: (x, y, w, h) em px da tela

    def ocupado(self, ini: float, fim: float) -> list[tuple[float, float, float, float]]:
        saida = []
        for t, cs in zip(self.tempos, self.caixas):
            if ini - 0.25 <= t <= fim + 0.25:
                saida += cs
        return saida


def mapear(video: Path, fps_amostra: float = 4.0, log=None) -> MapaRostos:
    """Rostos no vídeo montado (1080x1920), amostrados a `fps_amostra`."""
    import cv2
    from .enquadramento import _MODELO
    w, h = 360, 640  # detecção em 1/3 da resolução
    modelo = np.frombuffer(_MODELO.read_bytes(), np.uint8)
    det = cv2.FaceDetectorYN.create("onnx", modelo, np.empty(0, np.uint8), (w, h), 0.6, 0.3, 5000)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-an", "-vf", f"fps={fps_amostra},scale={w}:{h}",
                          "-pix_fmt", "bgr24", "-f", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    tempos, caixas = [], []
    n, k, esc = w * h * 3, 0, W / w
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        q = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        _, achados = det.detect(q)
        cs = [(float(f[0]) * esc, float(f[1]) * esc, float(f[2]) * esc, float(f[3]) * esc) for f in (achados if achados is not None else [])]
        tempos.append(k / fps_amostra)
        caixas.append(cs)
        k += 1
    p.wait()
    if log:
        com = sum(1 for c in caixas if c)
        log(f"Mapa de espaço: {len(tempos)} amostras, rosto em {com}")
    return MapaRostos(tempos, caixas)


def _sobrepoe(z: tuple[int, int, int, int], c: tuple[float, float, float, float]) -> float:
    """Área de interseção entre a zona e o rosto (com margem)."""
    x, y, w, h = c
    mx, my = w * MARGEM, h * MARGEM
    x0, y0, x1, y1 = x - mx, y - my, x + w + mx, y + h + my * 1.5  # um pouco mais embaixo (queixo)
    zx0, zy0, zx1, zy1 = z[0], z[1], z[0] + z[2], z[1] + z[3]
    ix = max(0.0, min(x1, zx1) - max(x0, zx0))
    iy = max(0.0, min(y1, zy1) - max(y0, zy0))
    return ix * iy


LEGENDA_FAIXA = (1270, 1760)   # onde a legenda prefere ficar (terço inferior)
CENA_LIMITE = (110, 1250)      # ilustrações acima da área da legenda
MIN_W, MIN_H = 420, 230


def _ocupacao_y(rostos) -> list[tuple[float, float]]:
    """Intervalos verticais ocupados por rostos (com margem; um pouco mais embaixo, por causa do queixo)."""
    ivs = sorted((y - h * MARGEM, y + h + h * MARGEM * 1.6) for _, y, _, h in rostos)
    juntos: list[list[float]] = []
    for a, b in ivs:
        if juntos and a <= juntos[-1][1]:
            juntos[-1][1] = max(juntos[-1][1], b)
        else:
            juntos.append([a, b])
    return [(a, b) for a, b in juntos]


def _faixas_livres(ocup: list[tuple[float, float]], lim: tuple[int, int]) -> list[tuple[int, int]]:
    livres, y = [], lim[0]
    for a, b in ocup:
        if a > y:
            livres.append((y, min(a, lim[1])))
        y = max(y, b)
    if y < lim[1]:
        livres.append((y, lim[1]))
    return [(int(a), int(b)) for a, b in livres if b - a > 0]


def caixa_livre(mapa: MapaRostos | None, ini: float, fim: float, tipo: str) -> tuple[str, tuple[int, int, int, int]]:
    """(nome, caixa x,y,w,h) livre de rostos durante [ini, fim]. Faixas de largura total acima/abaixo/entre rostos;
    para cenas, também as laterais de um rosto único."""
    rostos = mapa.ocupado(ini, fim) if mapa else []
    ocup = _ocupacao_y(rostos)
    if tipo == "legenda":
        for a, b in _faixas_livres(ocup, LEGENDA_FAIXA):
            if b - a >= 200:
                return "base", (60, a, 960, b - a)
        faixas = sorted(_faixas_livres(ocup, (120, 1800)), key=lambda f: -(f[1] - f[0]))
        if faixas and faixas[0][1] - faixas[0][0] >= 160:
            a, b = faixas[0]
            return "faixa", (60, a, 960, b - a)
        return "base", (60, LEGENDA_FAIXA[0], 960, 420)  # sem espaço: fica embaixo (o rosto pode estar na base)
    candidatas = [("faixa", (60, a, 960, b - a)) for a, b in _faixas_livres(ocup, CENA_LIMITE)]
    if rostos:
        x0 = min(x - w * MARGEM for x, _, w, _ in rostos)
        x1 = max(x + w + w * MARGEM for x, _, w, _ in rostos)
        if x0 - 40 >= MIN_W * 0.75:
            candidatas.append(("esquerda", (30, 320, int(x0 - 40), 860)))
        if W - 30 - (x1 + 10) >= MIN_W * 0.75:
            candidatas.append(("direita", (int(x1 + 10), 320, int(W - 30 - x1 - 10), 860)))
    boas = [c for c in candidatas if c[1][2] >= MIN_W * 0.75 and c[1][3] >= MIN_H]
    if not boas:
        # sem espaço bom: a maior faixa livre que ainda dá para ler (a cena é reduzida); senão, nenhuma
        # sem espaço bom em volta do rosto: a cena vira um "corte" em tela cheia (fundo escuro texturizado), como as
        # cenas da referência — assim nada fica sobreposto ao rosto
        return "cheia", (40, 240, 1000, 1000)  # termina em 1240: a legenda continua embaixo
    # prefere a faixa mais alta da tela (perto do olhar) entre as que têm área boa
    return max(boas, key=lambda c: c[1][2] * min(c[1][3], 600) - c[1][1] * 120)


def zona_livre(mapa: MapaRostos | None, ini: float, fim: float, tipo: str) -> str:
    """Compatibilidade: só o nome da zona."""
    if tipo == "cheia":
        return "cheia"
    return caixa_livre(mapa, ini, fim, tipo)[0]


def aplicar(mapa: MapaRostos | None, grupos: list[dict], cenas: list[dict], log=None) -> None:
    """Grava `zona` (nome) e `caixa` (x, y, w, h) de cada linha de legenda e de cada cena."""
    for g in grupos:
        g["zona"], g["caixa"] = caixa_livre(mapa, g["ini"], g["fim"], "legenda")
    for c in cenas:
        if c.get("tipo") in ("imagem", "pintura", "citacao"):
            c["zona"] = "cheia"
            continue
        c["zona"], c["caixa"] = caixa_livre(mapa, c["ini"], c["fim"], "cena")
        if c["zona"] == "cheia":
            c["telaCheia"] = True
    # regra do cliente: nada sobre o rosto — cena sem espaço livre sai do corte
    cenas[:] = [c for c in cenas if c.get("zona") != "nenhuma"]
    # se uma cena e uma linha de legenda caem na mesma faixa ao mesmo tempo, a cena fica com a metade de cima
    for c in cenas:
        cx = c.get("caixa")
        if not cx or c.get("telaCheia"):
            continue
        for g in grupos:
            gx = g["caixa"]
            no_tempo = g["ini"] < c["fim"] and g["fim"] > c["ini"]
            na_faixa = gx[1] < cx[1] + cx[3] and cx[1] < gx[1] + gx[3]
            if no_tempo and na_faixa:
                meio = cx[3] // 2
                c["caixa"] = (cx[0], cx[1], cx[2], meio - 10)
                g["caixa"] = (gx[0], cx[1] + meio, gx[2], max(gx[1] + gx[3] - (cx[1] + meio), 200))
    if log:
        uso: dict[str, int] = {}
        for x in grupos:
            uso["legenda " + x["zona"]] = uso.get("legenda " + x["zona"], 0) + 1
        for c in cenas:
            uso["cena " + c["zona"]] = uso.get("cena " + c["zona"], 0) + 1
        log("Mapa de espaço: " + ", ".join(f"{k} ({v})" for k, v in uso.items()))
