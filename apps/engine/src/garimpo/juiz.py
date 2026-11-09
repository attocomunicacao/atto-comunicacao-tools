"""Juiz LLM local (Qwen3-4B, GGUF Q4_K_M, Apache-2.0, llama.cpp em CPU) para os finalistas de corte.

Mesmo desenho das ferramentas de corte automático (OpusClip, SupoClip etc.): a heurística acha janelas
candidatas e um LLM as avalia com uma rubrica de viralidade. Aqui a rubrica é:
- gancho: os 5 primeiros segundos prendem quem está rolando o feed?
- contexto: o trecho se sustenta sozinho, sem depender do que veio antes?
- valor: ensina, surpreende, emociona ou traz opinião forte?
- fechamento: termina com a ideia concluída?
- bastidor: contém conversa de gravação (contagem, "gravando", "pronto")?
- inicio: índice da frase onde o corte deveria começar para ter o gancho mais forte.

Rodar o LLM na transcrição inteira é inviável em CPU (ver diário 004); aqui ele lê só ~10-20 trechos
de 1 min, com saída JSON curta.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .modelos import Corte

SISTEMA = (
    "Você é editor de vídeos curtos (Reels, TikTok, Shorts) e avalia trechos de podcasts e palestras em português. "
    "Responda apenas com JSON."
)
PEDIDO = """Avalie o trecho abaixo para virar um vídeo curto. As frases estão numeradas; [0-5s] marca o que se ouve nos 5 primeiros segundos.

{frases}

Dê notas de 0 a 10:
- "gancho": os primeiros 5 segundos fazem a pessoa parar de rolar o feed? (abertura do programa, cumprimento, "então", "né" = nota baixa)
- "contexto": dá para entender sem ter visto o que veio antes?
- "valor": ensina algo, surpreende, emociona ou traz opinião forte?
- "fechamento": termina com a ideia concluída?
Também:
- "bastidor": true se houver conversa de gravação (contagem 1 2 3 / 5 4 3, "gravando", "pronto", teste de som, combinações da equipe).
- "inicio": número da frase onde o corte deveria começar para ter o melhor gancho mantendo o sentido (1 = como está).
- "impacto": número da frase mais forte, surpreendente ou polêmica do trecho, que funcionaria sozinha como chamada nos primeiros segundos do vídeo.

JSON: {{"gancho": n, "contexto": n, "valor": n, "fechamento": n, "bastidor": bool, "inicio": n, "impacto": n}}"""


@dataclass
class Avaliacao:
    gancho: float
    contexto: float
    valor: float
    fechamento: float
    bastidor: bool
    inicio: int  # índice (0 = primeira frase)
    impacto: int = 0  # índice da frase mais forte (candidata a "cold open")

    @property
    def nota(self) -> float:
        # o gancho pesa mais: são os 5 primeiros segundos que seguram a audiência
        return 0.4 * self.gancho + 0.25 * self.contexto + 0.25 * self.valor + 0.1 * self.fechamento


def _num(v, padrao: float = 5.0) -> float:
    """Aceita 8, "8", "8/10", "nota 8" (o Qwen3 varia o formato)."""
    m = re.search(r"\d+(?:[.,]\d+)?", str(v)) if v is not None else None
    if not m:
        return padrao
    return max(0.0, min(10.0, float(m.group(0).replace(",", "."))))


def interpretar(texto: str, n_frases: int) -> Avaliacao:
    m = re.search(r"\{.*\}", texto, re.S)
    d = json.loads(m.group(0)) if m else {}
    ini = int(_num(d.get("inicio", 1), 1)) - 1
    imp = int(_num(d.get("impacto", 1), 1)) - 1
    return Avaliacao(_num(d.get("gancho")), _num(d.get("contexto")), _num(d.get("valor")), _num(d.get("fechamento")),
                     bool(d.get("bastidor", False)), max(0, min(ini, n_frases - 1)), max(0, min(imp, n_frases - 1)))


def montar_prompt(c: Corte) -> str:
    ini = c.ini
    linhas = []
    for k, f in enumerate(c.frases[:14], 1):
        marca = " [0-5s]" if f.ini < ini + 5 else ""
        linhas.append(f"{k}.{marca} {f.texto.strip()}")
    return PEDIDO.format(frases="\n".join(linhas))


class Juiz:
    def __init__(self, caminho_modelo: str):
        from llama_cpp import Llama
        self.llm = Llama(model_path=caminho_modelo, n_ctx=4096, n_threads=os.cpu_count() or 8, verbose=False)

    def avaliar(self, c: Corte) -> Avaliacao:
        try:
            r = self.llm.create_chat_completion(
                messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": montar_prompt(c) + " /no_think"}],
                response_format={"type": "json_object"}, temperature=0.1, max_tokens=200)
            return interpretar(r["choices"][0]["message"]["content"], len(c.frases))
        except Exception:
            return Avaliacao(5, 5, 5, 5, False, 0, 0)


def carregar(log=None) -> Juiz | None:
    """Juiz pronto, ou None se o modelo não estiver disponível (aí vale só a heurística)."""
    if os.environ.get("ATTO_SEM_LLM"):
        return None
    try:
        from . import recursos
        caminho = recursos.llm(log)
        if log:
            log("Carregando o juiz de cortes (Qwen3-4B, CPU)")
        return Juiz(str(caminho))
    except Exception as e:
        if log:
            log(f"Juiz LLM indisponível ({e}); usando só a pontuação heurística")
        return None
