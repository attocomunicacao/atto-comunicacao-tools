"""Modelos grandes: localiza no computador ou baixa uma vez (com progresso) do Hugging Face.

O pacote do app tem limite de 2 GB por arquivo no GitHub, então os modelos grandes (Whisper large-v3-turbo,
~1,6 GB, e o LLM local Qwen3-4B, ~2,5 GB) vêm na primeira vez que são usados e ficam em ATTO_CACHE
(o app aponta para a pasta de dados do usuário). O Whisper `small` continua embutido como plano B offline.
"""
from __future__ import annotations

import os
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
