"""Laboratório de animação do Garimpo: gera cenários, renderiza pela camada ATTO Motion, mede a fluidez quadro a quadro
e compara com as medidas das referências. Cada rodada vira uma pasta em `lab/rodadas/` e atualiza o banco
`docs/animacoes/banco.json`.

Uso (dentro de apps/engine, com ATTO_MOTION_CMD apontando para o renderizador):
    uv run python -m garimpo.lab                 # todos os cenários
    uv run python -m garimpo.lab sobe conceito   # só alguns
    uv run python -m garimpo.lab --listar

Métricas (sobre a diferença entre o quadro renderizado e o fundo):
- entrada_s: do 1º quadro com o elemento até 95% da área final (referência: palavra entra em 5-6 quadros ≈ 0,17-0,35 s);
- saida_s: de 95% a 5% da área no fim (referência: bloco some em ~4-5 quadros ≈ 0,13-0,2 s);
- salto: maior variação de área entre quadros vizinhos fora de entrada/saída (pulo/piscada; ideal ≈ 0);
- tremor: média do |aceleração| do centro do elemento em px/quadro² (ideal baixo — movimento contínuo e suave);
- deriva_px: quanto o elemento anda enquanto está "parado" (referência: o bloco nunca para, ~5-15 px);
- cobertura: fração máxima da tela ocupada (sanidade: legenda < 25%, tela cheia > 60%).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
BANCO = RAIZ / "docs" / "animacoes" / "banco.json"
RODADAS = RAIZ / "lab" / "rodadas"
FPS = 30.0

# Faixas-alvo medidas nas referências (docs/pesquisa/2026-11-referencias-v07.md)
ALVO = {
    "legenda": {"entrada_s": (0.15, 0.45), "saida_s": (0.05, 0.30), "salto": (0.0, 0.18), "tremor": (0.0, 2.5),
                "deriva_px": (3.0, 30.0), "cobertura": (0.01, 0.25)},
    "cena": {"entrada_s": (0.25, 1.0), "saida_s": (0.1, 0.5), "salto": (0.0, 0.2), "tremor": (0.0, 3.0),
             "cobertura": (0.03, 0.6)},  # deriva não vale nas cenas: traços desenhados mudam o topo
    "tela": {"entrada_s": (0.0, 0.8), "saida_s": (0.1, 0.5), "salto": (0.0, 0.25), "tremor": (0.0, 4.0),
             "cobertura": (0.5, 1.0)},
}


def _palavras(frase: str, ini: float, passo: float = 0.32) -> list[dict]:
    ws = frase.split()
    return [{"t": w.strip("[]").lower(), "ini": round(ini + i * passo, 3), "fim": round(ini + i * passo + passo * 0.9, 3),
             "chave": w.startswith("[")} for i, w in enumerate(ws)]


def _grupo(frase: str, ini: float, preset: str, pont: str = "") -> dict:
    ps = _palavras(frase, ini, passo=0.8)   # palavras espaçadas: cada entrada fica isolada na medida
    return {"ini": ps[0]["ini"], "fim": round(ps[-1]["fim"] + 0.9, 3), "palavras": ps, "preset": preset, "pont": pont,
            "caixa": [90, 1180, 840, 420]}


PRESETS_LEGENDA = ["cinematico", "maquina", "sobe", "desce", "esquerda", "direita", "elastico", "deslocamento",
                   "impacto", "revelacao", "glitch"]
FRASES = {"maquina": ("qual foi a tua [percepção]", "?"), "elastico": ("são [75] milhões", ""),
          "esquerda": ("mas ele [nunca] começa", ""), "direita": ("porém a [política] tem tempo", "")}


def cenarios() -> dict[str, dict]:
    """Um job de motion por animação (legenda: 1 linha; cenas: 1 cena), 3,2 s cada."""
    cs: dict[str, dict] = {}
    for p in PRESETS_LEGENDA:
        frase, pont = FRASES.get(p, ("sobre uma nova [lei] trabalhista", ""))
        g = _grupo(frase, 0.4, p, pont)
        cs[p] = {"categoria": "legenda", "duracao": 5.6, "grupos": [g], "cenas": [], "palavras": g["palavras"]}
    cenas = {
        "destaque": {"tipo": "destaque", "texto": "o que muda na prática"},
        "numero": {"tipo": "numero", "valor": 75, "sufixo": " mi", "texto": "pessoas afetadas"},
        "comparacao": {"tipo": "comparacao", "antes": "44h", "depois": "40h", "texto": "jornada semanal"},
        "icone": {"tipo": "icone", "icone": "Scale", "texto": "nova lei"},
        "documento": {"tipo": "documento", "texto": "PEC muda a jornada de trabalho no país", "destaque": "jornada",
                      "rotulo": "CONGRESSO"},
        "citacao": {"tipo": "citacao", "texto": "ele nunca começa pela consequência", "cobreLegenda": True},
        "conceito": {"tipo": "conceito", "texto": "a lei muda o caixa da empresa", "destaque": "caixa",
                     "icone": "Scale", "cobreLegenda": True},
    }
    for nome, c in cenas.items():
        cena = {**c, "ini": 0.3, "fim": 3.0, "caixa": [60, 160, 960, 900]}
        cat = "tela" if nome in ("citacao", "conceito") else "cena"
        cs[nome] = {"categoria": cat, "duracao": 3.4, "grupos": [], "cenas": [cena], "palavras": []}
    return cs


def _fundo(arq: Path, dur: float) -> None:
    """Fundo neutro com leve textura (o render compara com ele)."""
    if arq.exists():
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x2a2d33:s=1080x1920:r={FPS:g}:d={dur}",
                    "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(dur), "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(arq)], check=True)


def renderizar(nome: str, cen: dict, pasta: Path) -> Path:
    from . import midia
    base = pasta / f"fundo-{cen['duracao']}.mp4"
    _fundo(base, cen["duracao"])
    job = {"fps": FPS, "duracao": cen["duracao"], "largura": 1080, "altura": 1920, "palavras": cen["palavras"],
           "grupos": cen["grupos"], "cenas": cen["cenas"], "transicoes": []}
    saida = pasta / f"{nome}.mp4"
    midia.aplicar_motion(base, job, saida)
    return saida


def _quadros(arq: Path) -> np.ndarray:
    """Quadros em cinza, 1/4 da resolução (270x480)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-vf", "scale=270:480,format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, 480, 270).astype(np.int16)


def medir(arq: Path, fundo: Path) -> dict:
    q = _quadros(arq)
    f = _quadros(fundo)[0]
    dif = np.abs(q - f)
    masc = dif > 18                                # o que a animação desenhou (para o centro)
    # intensidade (não só área): capta a palavra indo de cinza a branco, o desfoque e a opacidade
    area = (np.clip(dif, 0, 200) / 200.0).mean(axis=(1, 2))
    area = np.maximum(area - area[:4].max(), 0.0)  # tira o ruído de compressão (os cenários começam vazios)
    n = len(area)
    if area.max() < 1e-4:
        return {"vazio": True}
    pico = float(np.percentile(area[area > 0], 90))
    # limiar absoluto: uma palavra pequena sozinha pode ficar abaixo de 5% do pico do bloco inteiro
    vivo = np.nonzero(area > max(2e-4, 0.002 * pico))[0]
    a0, a1 = int(vivo[0]), int(vivo[-1])
    cheio = np.nonzero(area >= 0.95 * pico)[0]
    c0, c1 = int(cheio[0]), int(cheio[-1])
    # entrada do 1º elemento: do 1º quadro visível até 90% do nível que ele tem 0,6 s depois (antes do 2º)
    nivel = area[min(a0 + int(0.5 * FPS), n - 1)]  # 0,5 s: cobre o alvo (≤ 0,45) sem pegar a 2ª palavra
    e1 = next((k for k in range(a0, n) if area[k] >= 0.9 * nivel), a0)
    # saída: do último quadro com 90% do nível de 0,6 s antes do fim até sumir
    nivel_s = area[max(a1 - int(0.6 * FPS), 0)]
    s1 = next((k for k in range(a1, a0, -1) if area[k] >= 0.9 * nivel_s), a1)
    ys, xs = np.mgrid[0:480, 0:270]
    centros = []
    for k in range(n):
        m = masc[k]
        s = m.sum()
        centros.append((float((xs * m).sum() / s), float((ys * m).sum() / s)) if s > 20 else (np.nan, np.nan))
    cen = np.array(centros) * 4                    # volta para px de 1080x1920
    meio = slice(c0, c1 + 1)
    da = np.abs(np.diff(area[meio])) / max(pico, 1e-6)
    v = np.diff(cen[meio], axis=0)
    acc = np.linalg.norm(np.diff(v, axis=0), axis=1)
    # deriva: o topo do 1º elemento (o layout é fixo; só a deriva/entrada o movem) entre a entrada e +1 s
    def topo(k):
        linhas = np.nonzero(masc[k].any(axis=1))[0]
        return float(linhas[0]) * 4 if len(linhas) else np.nan
    k2 = min(e1 + int(1.0 * FPS), max(s1 - 1, e1))
    deriva = abs(topo(k2) - topo(e1)) if k2 > e1 else 0.0
    deriva = 0.0 if np.isnan(deriva) else deriva
    return {
        "entrada_s": round((e1 - a0) / FPS, 3),
        "montagem_s": round((c0 - a0) / FPS, 3),   # até o bloco inteiro estar na tela
        "saida_s": round((a1 - s1) / FPS, 3),
        "salto": round(float(np.nanmax(da)) if len(da) else 0.0, 3),
        "tremor": round(float(np.nanmean(acc)) if len(acc) else 0.0, 3),
        "deriva_px": round(float(deriva), 1),
        "cobertura": round(float(masc.mean(axis=(1, 2)).max()), 3),
    }


def avaliar(cat: str, m: dict) -> tuple[float, list[str]]:
    """Nota 0-10 (10 = dentro de todas as faixas da referência) e a lista do que está fora."""
    if m.get("vazio"):
        return 0.0, ["nada foi desenhado"]
    fora = []
    for k, (lo, hi) in ALVO[cat].items():
        x = m.get(k)
        if x is None:
            continue
        if not lo <= x <= hi:
            fora.append(f"{k}={x} (alvo {lo}-{hi})")
    return round(10 * (1 - len(fora) / len(ALVO[cat])), 1), fora


def folha(arq: Path, saida: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(arq), "-vf", "fps=10,scale=180:320,tile=8x4",
                    "-frames:v", "1", str(saida)], check=False)


def carregar_banco() -> dict:
    if BANCO.exists():
        return json.loads(BANCO.read_text(encoding="utf-8"))
    return {"versao": 1, "animacoes": {}, "rodadas": []}


def rodar(nomes: list[str] | None = None, nota: str = "") -> Path:
    cs = cenarios()
    alvo = {k: v for k, v in cs.items() if not nomes or k in nomes}
    pasta = RODADAS / time.strftime("%Y%m%d-%H%M%S")
    pasta.mkdir(parents=True, exist_ok=True)
    banco = carregar_banco()
    linhas = [f"# Rodada {pasta.name}", "", nota, "", "| Animação | Categoria | Nota | Entrada s | Saída s | Salto | Tremor | Deriva px | Fora da referência |",
              "|---|---|---|---|---|---|---|---|---|"]
    resumo = {}
    for nome, cen in alvo.items():
        try:
            mp4 = renderizar(nome, cen, pasta)
            m = medir(mp4, pasta / f"fundo-{cen['duracao']}.mp4")
            folha(mp4, pasta / f"{nome}.png")
        except Exception as e:  # um cenário quebrado não para a rodada
            m = {"vazio": True, "erro": str(e)[:200]}
        n, fora = avaliar(cen["categoria"], m)
        resumo[nome] = {"nota": n, **m}
        linhas.append(f"| {nome} | {cen['categoria']} | {n} | {m.get('entrada_s', '-')} | {m.get('saida_s', '-')} | "
                      f"{m.get('salto', '-')} | {m.get('tremor', '-')} | {m.get('deriva_px', '-')} | {'; '.join(fora) or 'ok'} |")
        item = banco["animacoes"].setdefault(nome, {"categoria": cen["categoria"], "historico": []})
        item["ultima"] = {"rodada": pasta.name, "nota": n, "metricas": m, "fora": fora}
        item["historico"] = (item.get("historico", []) + [{"rodada": pasta.name, "nota": n}])[-30:]
        print(f"{nome:14s} nota {n:4.1f}  {'; '.join(fora) or 'ok'}", flush=True)
    media = round(sum(r["nota"] for r in resumo.values()) / max(len(resumo), 1), 2)
    linhas += ["", f"Média: **{media}**"]
    banco["rodadas"] = (banco.get("rodadas", []) + [{"rodada": pasta.name, "media": media, "nota": nota,
                                                      "cenarios": len(resumo)}])[-200:]
    (pasta / "relatorio.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (pasta / "metricas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    BANCO.write_text(json.dumps(banco, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"MEDIA {media}  PASTA {pasta}", flush=True)
    return pasta


def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if "--listar" in args:
        print("\n".join(f"{k} ({v['categoria']})" for k, v in cenarios().items()))
        return
    nota = ""
    if "--nota" in args:
        i = args.index("--nota")
        nota = args[i + 1]
        args = args[:i] + args[i + 2:]
    if not os.environ.get("ATTO_MOTION_CMD"):
        raiz = str(RAIZ).replace("\\", "/")
        os.environ["ATTO_MOTION_CMD"] = json.dumps([f"{raiz}/node_modules/electron/dist/electron.exe",
                                                    f"{raiz}/apps/desktop", "--render-motion"])
    rodar(args or None, nota)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- transições (zoom inicial)

def curva_zoom(video: str, ini: float, dur: float, fps: float = 30.0) -> list[float]:
    """Escala de cada quadro em relação ao último da janela (1,0 = assentado), por ORB + afim parcial."""
    import cv2
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ini), "-t", str(dur), "-i", video, "-vf",
                        f"fps={fps:g},scale=360:640,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True)
    q = np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, 640, 360)
    orb = cv2.ORB_create(1500)
    kb, db = orb.detectAndCompute(q[-1], None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    saida = []
    for f in q:
        ka, da = orb.detectAndCompute(f, None)
        if da is None or db is None:
            saida.append(float("nan"))
            continue
        ms = sorted(bf.match(da, db), key=lambda m: m.distance)[:300]
        if len(ms) < 12:
            saida.append(float("nan"))
            continue
        a = np.float32([ka[m.queryIdx].pt for m in ms])
        b = np.float32([kb[m.trainIdx].pt for m in ms])
        M, _ = cv2.estimateAffinePartial2D(b, a, method=cv2.RANSAC)
        saida.append(round(float(np.hypot(M[0, 0], M[1, 0])), 3) if M is not None else float("nan"))
    return saida


def medir_zoom(video: str, ini: float, dur: float) -> dict:
    """tempo até assentar (escala < 1,03) e escala do 1º quadro."""
    c = curva_zoom(video, ini, dur)
    validos = [x for x in c if x == x]
    t = next((k for k, x in enumerate(c) if x == x and x < 1.03), len(c)) / FPS
    return {"escala_inicial": validos[0] if validos else None, "assenta_s": round(t, 3), "curva": c[:30]}
