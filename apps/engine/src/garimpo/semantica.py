"""Camada semântica do Garimpo: embeddings de frase (multilingual-e5-small, MIT, ONNX int8 em CPU).

Para que serve (ver docs/pesquisa/2026-11-selecao-de-cortes.md):
- **temas**: fronteira onde o sentido muda (TextTiling com vetores em vez de contagem de palavras);
- **parágrafos**: quebra uma fala corrida quando o assunto vira, mesmo sem pausa longa;
- **relevância**: quanto um trecho conversa com a descrição que o usuário escreveu do vídeo;
- **coesão**: se o corte trata de uma ideia só (frases próximas do centro do corte);
- **centralidade**: qual oração resume o corte (melhor candidata a gancho / cold open).

Sem o modelo (offline na primeira vez), tudo isso volta ao comportamento lexical antigo.
"""
from __future__ import annotations

import os

import numpy as np

_cache: dict[str, np.ndarray] = {}


class Embeddings:
    def __init__(self, pasta):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(str(pasta / "tokenizer.json"))
        self.tok.enable_truncation(256)
        self.tok.enable_padding(pad_id=1, pad_token="<pad>")
        opc = ort.SessionOptions()
        opc.intra_op_num_threads = os.cpu_count() or 4
        self.sess = ort.InferenceSession(str(pasta / "model.onnx"), opc, providers=["CPUExecutionProvider"])
        self.entradas = {i.name for i in self.sess.get_inputs()}

    def vetores(self, textos: list[str], tipo: str = "passage", lote: int = 32) -> np.ndarray:
        """Vetores normalizados (n, 384). `tipo`: "query" para a descrição do usuário, "passage" para a fala."""
        saida = np.zeros((len(textos), 384), dtype=np.float32)
        faltam = []
        for i, t in enumerate(textos):
            k = f"{tipo}: {t.strip()}"
            if k in _cache:
                saida[i] = _cache[k]
            else:
                faltam.append(i)
        for a in range(0, len(faltam), lote):
            idx = faltam[a:a + lote]
            cod = self.tok.encode_batch([f"{tipo}: {textos[i].strip()}" for i in idx])
            ids = np.array([c.ids for c in cod], dtype=np.int64)
            mask = np.array([c.attention_mask for c in cod], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.entradas:
                feed["token_type_ids"] = np.zeros_like(ids)
            h = self.sess.run(None, feed)[0]                       # (b, t, 384)
            m = mask[..., None].astype(np.float32)
            v = (h * m).sum(1) / np.maximum(m.sum(1), 1e-6)        # média com máscara (receita do e5)
            v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
            for j, i in enumerate(idx):
                saida[i] = v[j]
                _cache[f"{tipo}: {textos[i].strip()}"] = v[j]
        return saida


_modelo: Embeddings | None = None
_falhou = False


def carregar(log=None) -> Embeddings | None:
    """Modelo pronto (baixa ~120 MB na primeira vez) ou None, caindo para o modo lexical."""
    global _modelo, _falhou
    if _modelo is not None or _falhou or os.environ.get("ATTO_SEM_SEMANTICA"):
        return _modelo
    try:
        from . import recursos
        _modelo = Embeddings(recursos.embeddings(log))
        if log:
            log("Camada semântica pronta (multilingual-e5-small, CPU)")
    except Exception as e:
        _falhou = True
        if log:
            log(f"Camada semântica indisponível ({str(e)[:80]}); usando só vocabulário")
    return _modelo


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def centro(vs: np.ndarray) -> np.ndarray:
    c = vs.mean(0)
    return c / max(float(np.linalg.norm(c)), 1e-9)


def coesao(vs: np.ndarray) -> float:
    """0-1: média da similaridade de cada frase com o centro do trecho (uma ideia só = alto)."""
    if len(vs) < 2:
        return 1.0
    return float((vs @ centro(vs)).mean())


def profundidades(sim: list[float]) -> list[float]:
    """Profundidade de cada vale (TextTiling): quanto a similaridade cai em relação aos picos vizinhos."""
    d = []
    for i, s in enumerate(sim):
        # picos locais mais próximos (sobe enquanto cresce)
        j = i
        while j > 0 and sim[j - 1] >= sim[j]:
            j -= 1
        esq = sim[j]
        j = i
        while j < len(sim) - 1 and sim[j + 1] >= sim[j]:
            j += 1
        dir_ = sim[j]
        d.append((esq - s) + (dir_ - s))
    return d
