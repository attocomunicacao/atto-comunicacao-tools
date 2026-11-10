"""Modelos grandes: localiza no computador ou baixa uma vez (com progresso) do Hugging Face.

O pacote do app tem limite de 2 GB por arquivo no GitHub, então os modelos grandes (Whisper large-v3-turbo,
~1,6 GB, e o LLM local Qwen3-4B, ~2,5 GB) vêm na primeira vez que são usados e ficam em ATTO_CACHE
(o app aponta para a pasta de dados do usuário). O Whisper `small` continua embutido como plano B offline.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
from pathlib import Path

WHISPER = {
    "large-v3-turbo": ("mobiuslabsgmbh/faster-whisper-large-v3-turbo",
                       ["config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "model.bin"]),
}
LLM = ("Qwen/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf")  # Apache-2.0 (uso comercial liberado)


def pasta_cache() -> Path:
    base = os.environ.get("ATTO_CACHE")
    p = Path(base) if base else Path.home() / ".cache" / "atto-tools"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _hf_local(repo: str, arquivo: str) -> Path | None:
    """Arquivo já baixado pelo huggingface_hub (desenvolvimento)."""
    raiz = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{repo.replace('/', '--')}" / "snapshots"
    if raiz.exists():
        for snap in raiz.iterdir():
            if (snap / arquivo).exists():
                return snap / arquivo
    return None


def baixar(repo: str, arquivo: str, destino: Path, log=None, progresso=None) -> Path:
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{repo}/resolve/main/{arquivo}"
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    req = urllib.request.Request(url, headers={"User-Agent": "atto-tools"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        if log and total > 50e6:
            log(f"Baixando {arquivo} ({total / 1e9:.1f} GB), só na primeira vez")
        feito, ultimo = 0, -1
        while bloco := r.read(1 << 20):
            f.write(bloco)
            feito += len(bloco)
            if progresso and total:
                progresso(feito / total)
            if log and total > 50e6 and (pct := int(feito * 10 / total)) != ultimo:
                ultimo = pct
                log(f"  {arquivo}: {feito / 1e6:.0f} de {total / 1e6:.0f} MB")
    tmp.replace(destino)
    return destino


def whisper(nome: str, log=None, progresso=None) -> str:
    """Caminho (ou nome) para o WhisperModel. Ordem: embutido no app, cache do usuário, HF local, download."""
    embutido = Path(os.environ.get("ATTO_MODELOS", "")) / nome
    if os.environ.get("ATTO_MODELOS") and (embutido / "model.bin").exists():
        return str(embutido)
    if nome not in WHISPER:
        return nome
    repo, arquivos = WHISPER[nome]
    local = _hf_local(repo, "model.bin")
    if local:
        return str(local.parent)
    pasta = pasta_cache() / "whisper" / nome
    for a in arquivos:
        baixar(repo, a, pasta / a, log, progresso if a == "model.bin" else None)
    return str(pasta)


def llm(log=None, progresso=None) -> Path:
    repo, arquivo = LLM
    embutido = Path(os.environ.get("ATTO_MODELOS", "")) / "llm" / arquivo
    if os.environ.get("ATTO_MODELOS") and embutido.exists():
        return embutido
    return _hf_local(repo, arquivo) or baixar(repo, arquivo, pasta_cache() / "llm" / arquivo, log, progresso)


# multilingual-e5-small (MIT), ONNX int8 (~120 MB): embeddings de frase para temas, relevância e coesão
EMBEDDINGS = ("intfloat/multilingual-e5-small", ["onnx/model_qint8_avx512_vnni.onnx", "onnx/tokenizer.json"])


def embeddings(log=None) -> Path:
    """Pasta com `model.onnx` e `tokenizer.json` do e5-small (embutido, cache do usuário ou download)."""
    embutido = Path(os.environ.get("ATTO_MODELOS", "")) / "e5-small"
    if os.environ.get("ATTO_MODELOS") and (embutido / "model.onnx").exists():
        return embutido
    repo, arquivos = EMBEDDINGS
    pasta = pasta_cache() / "e5-small"
    for a in arquivos:
        nome = "model.onnx" if a.endswith(".onnx") else Path(a).name
        baixar(repo, a, pasta / nome, log)
    return pasta


# ---------------------------------------------------------------- pinturas em domínio público (Met Museum, CC0)

MET = "https://collectionapi.metmuseum.org/public/collection"


def _json(url: str):
    import json as _j
    req = urllib.request.Request(url, headers={"User-Agent": "atto-tools"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return _j.loads(r.read().decode("utf-8"))


titulos_usados: set[str] = set()  # a mesma obra não se repete na mesma exportação


def pintura(consulta: str, evitar: set[int] | None = None, log=None) -> tuple[Path, str] | None:
    """Uma pintura em domínio público do Metropolitan Museum (Open Access, CC0) para o tema. Cache por obra.

    Retorna (arquivo .jpg, crédito "Título — Artista") ou None (sem internet/sem resultado)."""
    evitar = evitar or set()
    pasta = pasta_cache() / "pinturas"
    try:
        ids = _json(f"{MET}/v1.1/search?q={urllib.parse.quote(consulta)}&hasImages=true&medium=Paintings&limit=12").get("objectIDs") or []
        for oid in ids:
            if oid in evitar:
                continue
            o = _json(f"{MET}/v1/objects/{oid}")
            url = o.get("primaryImageSmall") or o.get("primaryImage")
            if not o.get("isPublicDomain") or not url or o.get("title") in titulos_usados:
                continue
            arq = pasta / f"met-{oid}.jpg"
            if not arq.exists():
                baixar_url(url, arq)
            credito = " — ".join(x for x in (o.get("title"), o.get("artistDisplayName")) if x)
            evitar.add(oid)
            titulos_usados.add(o.get("title"))
            break
        else:
            return None
    except Exception as e:
        if log:
            log(f"Sem pintura para “{consulta}” ({e})")
        return None
    if log:
        log(f"Pintura para “{consulta}”: {credito} (Met Museum, domínio público)")
    return arq, credito


def baixar_url(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "atto-tools"})
    with urllib.request.urlopen(req, timeout=60) as r:
        destino.write_bytes(r.read())
    return destino
