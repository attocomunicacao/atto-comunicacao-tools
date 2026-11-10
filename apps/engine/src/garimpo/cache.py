"""Cache global por conteúdo: o mesmo vídeo nunca é transcrito duas vezes, mesmo num projeto novo.

O app cria uma pasta de projeto nova a cada análise (`projetos/<nome>-<data>`), então guardar a transcrição só na
pasta do projeto não bastava (falha relatada na v0.6). Aqui a chave é o **conteúdo** do arquivo:
tamanho + data de modificação + SHA-1 de 3 amostras de 4 MB (começo, meio, fim) — rápido mesmo em vídeos de 10 GB.

Pastas (em `ATTO_DADOS`, que o app aponta para `%APPDATA%/ATTO Tools/cache`):
- `transcricoes/<chave>.json`  — palavras com tempo (chave inclui modelo, versão do motor e termos do dicionário);
- `vetores/<chave>.npy`        — vetores de sentido das frases (estruturação);
- `juiz/<chave>.json`          — notas do juiz LLM por trecho (mesmo prompt = mesma nota).
Mudar `VERSAO_TRANSCRICAO`/`VERSAO_ESTRUTURA` invalida o que foi gerado por versões antigas do motor.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

VERSAO_TRANSCRICAO = "t3"  # v0.7: filtro de alucinação + tempos refinados pela energia do áudio
VERSAO_ESTRUTURA = "e1"
AMOSTRA = 4 << 20


def pasta(sub: str) -> Path:
    base = os.environ.get("ATTO_DADOS")
    if base:
        raiz = Path(base)
    else:
        from . import recursos
        raiz = recursos.pasta_cache() / "cache"
    p = raiz / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def impressao(arquivo: Path) -> str:
    """Identidade do conteúdo do arquivo (não do nome nem da pasta)."""
    st = arquivo.stat()
    h = hashlib.sha1(f"{st.st_size}:{int(st.st_mtime)}".encode())
    with open(arquivo, "rb") as f:
        for pos in (0, max(0, st.st_size // 2 - AMOSTRA // 2), max(0, st.st_size - AMOSTRA)):
            f.seek(pos)
            h.update(f.read(AMOSTRA))
    return h.hexdigest()[:20]


def chave(*partes) -> str:
    return hashlib.sha1(json.dumps(partes, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def chave_transcricao(video: Path, modelo: str, termos: list[str]) -> str:
    return chave(impressao(video), modelo, VERSAO_TRANSCRICAO, sorted(termos))


def ler_json(sub: str, k: str):
    arq = pasta(sub) / f"{k}.json"
    if arq.exists():
        try:
            return json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def gravar_json(sub: str, k: str, dados) -> None:
    arq = pasta(sub) / f"{k}.json"
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    tmp.replace(arq)


def vetores(textos: list[str], calcular):
    """Vetores das frases com cache: `calcular(textos)` só roda se esse conjunto de frases nunca foi visto."""
    import numpy as np
    arq = pasta("vetores") / f"{chave(VERSAO_ESTRUTURA, textos)}.npy"
    if arq.exists():
        try:
            v = np.load(arq)
            if len(v) == len(textos):
                return v, True
        except Exception:
            pass
    v = calcular(textos)
    np.save(arq, v)
    return v, False
