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
PEDIDO = """Avalie o trecho abaixo para virar um vídeo curto.{descricao}
As frases do trecho estão numeradas; [0-5s] marca o que se ouve nos 5 primeiros segundos.
ANTES e DEPOIS são as falas vizinhas, que NÃO entram no vídeo (servem para você julgar contexto e fechamento).

ANTES: {antes}
{frases}
DEPOIS: {depois}

Dê notas de 0 a 10, com rigor (7+ só para o que um editor profissional publicaria):
- "gancho": ouvindo SÓ os 5 primeiros segundos, a pessoa para de rolar o feed? Precisa ser uma frase completa e forte: afirmação surpreendente, pergunta, número, conflito, promessa. Abertura do programa, cumprimento, "então", "né", frase pela metade = 0 a 3.
- "contexto": quem não viu o ANTES entende tudo? Pronome sem referência ("ele", "isso", "essa lei"), resposta sem a pergunta ou continuação de raciocínio = nota baixa.
- "valor": ensina algo, surpreende, emociona ou traz opinião forte?
- "fechamento": a última frase conclui a ideia? Se o DEPOIS continua o mesmo raciocínio ("porém", "mas", "e aí", conclusão que ficou de fora), ou se outra pessoa responde a uma pergunta, nota baixa.
- "relevancia": quanto o trecho serve ao objetivo descrito pelo usuário (sem descrição, 5).
Também:
- "bastidor": true se houver conversa de gravação (contagem 1 2 3 / 5 4 3, "gravando", "pronto", teste de som, combinações da equipe).
- "inicio": número da frase onde o corte deveria começar para ter o melhor gancho mantendo o sentido (1 = como está).
- "impacto": número da frase mais forte, surpreendente ou polêmica do trecho, que funcionaria sozinha como chamada nos primeiros segundos do vídeo.

JSON: {{"gancho": n, "contexto": n, "valor": n, "fechamento": n, "relevancia": n, "bastidor": bool, "inicio": n, "impacto": n}}"""


@dataclass
class Avaliacao:
    gancho: float
    contexto: float
    valor: float
    fechamento: float
    bastidor: bool
    inicio: int  # índice (0 = primeira frase)
    impacto: int = 0  # índice da frase mais forte (candidata a "cold open")
    relevancia: float = 5.0

    @property
    def nota(self) -> float:
        # o gancho pesa mais (os 5 primeiros segundos seguram a audiência); fechamento e contexto vêm em seguida,
        # porque as falhas da v0.6 foram fim cortando a fala e corte que não se sustenta sozinho
        return (0.32 * self.gancho + 0.2 * self.contexto + 0.18 * self.valor + 0.18 * self.fechamento
                + 0.12 * self.relevancia)


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
                     bool(d.get("bastidor", False)), max(0, min(ini, n_frases - 1)), max(0, min(imp, n_frases - 1)),
                     _num(d.get("relevancia")))


def montar_prompt(c: Corte, antes=None, depois=None, descricao: str = "") -> str:
    ini = c.ini
    linhas = []
    for k, f in enumerate(c.frases[:14], 1):
        marca = " [0-5s]" if f.ini < ini + 5 else ""
        linhas.append(f"{k}.{marca} {f.texto.strip()}")
    desc = f"\nObjetivo do usuário para os cortes: {descricao.strip()[:400]}" if descricao.strip() else ""
    return PEDIDO.format(frases="\n".join(linhas), descricao=desc,
                         antes=antes.texto.strip()[:300] if antes else "(início da gravação)",
                         depois=depois.texto.strip()[:300] if depois else "(fim da gravação)")


class Juiz:
    def __init__(self, caminho_modelo: str):
        from llama_cpp import Llama
        self.llm = Llama(model_path=caminho_modelo, n_ctx=4096, n_threads=os.cpu_count() or 8, verbose=False)

    def avaliar(self, c: Corte, antes=None, depois=None, descricao: str = "") -> Avaliacao:
        from . import cache
        pedido = montar_prompt(c, antes, depois, descricao) + " /no_think"
        k = cache.chave("juiz-v2", pedido)
        guardado = cache.ler_json("juiz", k)  # reteste do mesmo vídeo: mesma nota, sem rodar o LLM de novo
        if guardado:
            return interpretar(guardado, len(c.frases))
        try:
            r = self.llm.create_chat_completion(
                messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": pedido}],
                response_format={"type": "json_object"}, temperature=0.1, max_tokens=200)
            texto = r["choices"][0]["message"]["content"]
            cache.gravar_json("juiz", k, texto)
            return interpretar(texto, len(c.frases))
        except Exception:
            return Avaliacao(5, 5, 5, 5, False, 0, 0, 5)


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
