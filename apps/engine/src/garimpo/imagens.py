"""Imagens livres de direitos para ilustrar frases do corte, e mapa de profundidade para o efeito 3D.

Fontes, em ordem (pesquisa 2026-11, docs/pesquisa/2026-11-imagens.md):
1. Pexels (licença Pexels: uso comercial livre, sem atribuição obrigatória) — só se o usuário cadastrar uma chave
   gratuita no app (ATTO_PEXELS_KEY). Fotos modernas: escritório, pessoas, cidade, indústria.
2. Wikimedia Commons — SOMENTE arquivos em domínio público / CC0 / "No restrictions" (a licença é conferida
   em cada arquivo pelo `extmetadata`).
3. Openverse — filtro `license=cc0,pdm`.
4. Metropolitan Museum Open Access — pinturas CC0 (ver `recursos.pintura`).

Profundidade: Depth Anything V2 Small (ONNX, Apache-2.0), rodando no processador com onnxruntime. O mapa
(claro = perto) vai para a camada de motion, que faz a "câmera" avançar com parallax (efeito 2.5D/3D).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from . import recursos

UA = "atto-tools/0.6 (github.com/attocomunicacao/atto-comunicacao-tools)"
LIVRES = ("public domain", "cc0", "no restrictions", "pd", "pdm")
# Nada de imagem que possa constranger o cliente (política, violência, pessoas identificáveis em situação sensível).
SENSIVEIS = ("protest", "protesto", "manifesta", "riot", "police", "policia", "polícia", "war", "guerra", "army",
             "military", "dead", "death", "morte", "blood", "nude", "naked", "bolsonar", "lula", "trump", "expuls",
             "fire", "incêndio", "accident", "acidente", "funeral", "prison", "prisão", "weapon", "gun",
             # v0.7: nada de figura política/pública (a foto do Reagan entrou num corte de teste)
             "president", "presidente", "reagan", "senator", "senador", "governor", "governador", "minister",
             "ministro", "congress", "congresso", "parliament", "white house", "politic", "elei", "election",
             "campaign", "deputad", "king", "queen", "prince", "pope", "papa ", "secretary", "ambassador",
             "official portrait", "meeting with", "visit of", "oval office")
STOP_EN = {"the", "a", "an", "of", "with", "and", "in", "on", "for", "at", "to"}


def _relevante(titulo: str, consulta: str) -> bool:
    t = titulo.lower()
    if any(x in t for x in SENSIVEIS):
        return False
    termos = [w for w in consulta.lower().split() if w not in STOP_EN and len(w) > 2]
    return any(w.rstrip("s") in t for w in termos)
PROFUNDIDADE = ("onnx-community/depth-anything-v2-small", "onnx/model.onnx")


def _get(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _pexels(q: str, usados: set[str]):
    chave = os.environ.get("ATTO_PEXELS_KEY")
    if not chave:
        return None
    d = _get(f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&orientation=portrait&per_page=8",
             {"Authorization": chave})
    for f in d.get("photos", []):
        url = f["src"].get("large2x") or f["src"].get("large")
        if url and url not in usados:
            return url, f"Foto: {f.get('photographer', 'Pexels')} (Pexels)", "pexels"
    return None


def _commons(q: str, usados: set[str]):
    # primeiro só fotos curadas (Quality/Featured), depois a busca geral
    for filtro in (" incategory:Quality_images", " incategory:Featured_pictures_on_Wikimedia_Commons", ""):
        r = _commons_busca(q, filtro, usados)
        if r:
            return r
    return None


def _commons_busca(q: str, filtro: str, usados: set[str]):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6"
           f"&gsrsearch={urllib.parse.quote(q + ' filetype:bitmap' + filtro)}&gsrlimit=15&prop=imageinfo"
           "&iiprop=url|extmetadata|size&iiurlwidth=1280&format=json")
    d = _get(api)
    paginas = sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in paginas:
        ii = (p.get("imageinfo") or [{}])[0]
        lic = (ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value") or "").lower()
        url = ii.get("thumburl") or ii.get("url")
        if not url or url in usados or not any(l in lic for l in LIVRES):
            continue
        if ii.get("width", 0) < 800:
            continue
        titulo = p.get("title", "").replace("File:", "").rsplit(".", 1)[0][:60]
        descricao = (ii.get("extmetadata", {}).get("ImageDescription", {}).get("value") or "")[:400]
        if not _relevante(titulo + " " + descricao, q):
            continue
        return url, f"{titulo} (Wikimedia Commons, domínio público)", "commons"
    return None


def _openverse(q: str, usados: set[str]):
    d = _get(f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(q)}&license=cc0,pdm&page_size=10")
    for r in d.get("results", []):
        url = r.get("url")
        if url and url not in usados and (r.get("width") or 0) >= 800 and _relevante(r.get("title") or "", q):
            return url, f"{(r.get('title') or '')[:60]} ({r.get('source', 'Openverse')}, {r.get('license', 'cc0').upper()})", "openverse"
    return None


def buscar(consulta: str, usados: set[str], log=None) -> tuple[Path, str] | None:
    """Primeira imagem livre que achar para a consulta (em inglês). Cache local por URL."""
    import hashlib
    for fonte in (_pexels, _commons, _openverse):
        try:
            r = fonte(consulta, usados)
        except Exception as e:  # fonte fora do ar: tenta a próxima
            if log:
                log(f"  {fonte.__name__[1:]} indisponível ({str(e)[:60]})")
            continue
        if r:
            url, credito, nome = r
            arq = recursos.pasta_cache() / "imagens" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg")
            if not arq.exists():
                recursos.baixar_url(url, arq)
            usados.add(url)
            if log:
                log(f"Imagem para “{consulta}”: {credito}")
            return arq, credito
    r = recursos.pintura(consulta, log=None)
    if r and _relevante(r[1], consulta):
        if log:
            log(f"Imagem para “{consulta}”: {r[1]} (Met Museum, domínio público)")
        return r
    if log:
        log(f"Nenhuma imagem livre e relevante para “{consulta}”; a frase fica sem imagem")
    return None


# ---------------------------------------------------------------- profundidade (efeito 3D)

_sessao = None


def profundidade(imagem: Path, log=None) -> Path | None:
    """Mapa de profundidade em PNG (claro = perto), do tamanho da imagem. None se o modelo não estiver disponível."""
    global _sessao
    import cv2
    import numpy as np
    saida = imagem.with_suffix(".prof.png")
    if saida.exists():
        return saida
    try:
        if _sessao is None:
            import onnxruntime as ort
            repo, arquivo = PROFUNDIDADE
            modelo = recursos.pasta_cache() / "profundidade" / "depth-anything-v2-small.onnx"
            recursos.baixar(repo, arquivo, modelo, log)
            _sessao = ort.InferenceSession(str(modelo), providers=["CPUExecutionProvider"])
        img = cv2.imdecode(np.frombuffer(imagem.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        x = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (518, 518), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
        x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        x = x.transpose(2, 0, 1)[None]
        nome = _sessao.get_inputs()[0].name
        d = _sessao.run(None, {nome: x})[0].squeeze()
        d = (d - d.min()) / max(float(d.max() - d.min()), 1e-6)
        d = cv2.resize((d * 255).astype(np.uint8), (w, h), interpolation=cv2.INTER_CUBIC)
        d = cv2.GaussianBlur(d, (0, 0), 3)  # bordas macias: sem "rasgos" no parallax
        cv2.imencode(".png", d)[1].tofile(str(saida))
        return saida
    except Exception as e:
        if log:
            log(f"Sem mapa de profundidade ({str(e)[:80]}); a imagem entra só com zoom")
        return None
