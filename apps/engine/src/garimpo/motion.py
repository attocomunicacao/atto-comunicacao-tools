"""Plano de motion de um corte: o que anima, quando (legenda, ilustrações, zooms e transições).

O motor decide; quem desenha é a camada ATTO Motion (HTML + GSAP, `apps/desktop/src/renderer/src/motion`),
renderizada quadro a quadro pelo próprio app (`--render-motion`). Ver `docs/motion.md`.

Ilustrações ("cenas") vêm de duas fontes:
- LLM local (o mesmo Qwen3-4B do juiz): lê as frases e propõe título-gancho e cenas (número, comparação, ícone,
  frase-chave) presas à frase em que o assunto aparece;
- regras (sempre rodam, e são o plano B): números com unidade ("75 milhões", "40%"), comparações ("de 44 para 40")
  e palavras-chave com ícone (jornada -> relógio, lei -> balança...).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .estrutura import STOP, _norm
from .modelos import Palavra

# Ícones Lucide permitidos (nome PascalCase do pacote lucide-static) e palavras que os chamam.
ICONES: dict[str, list[str]] = {
    "Clock": ["jornada", "hora", "horas", "tempo", "prazo", "relogio"],
    "Scale": ["lei", "leis", "justica", "juridico", "tribunal", "norma", "normas", "direito", "direitos", "clt"],
    "Landmark": ["governo", "congresso", "senado", "camara", "estado", "ministerio", "brasilia", "deputado", "deputada"],
    "Briefcase": ["trabalho", "trabalhador", "trabalhadores", "emprego", "empregos", "carreira", "profissional"],
    "Building2": ["empresa", "empresas", "industria", "setor", "comercio", "negocio", "negocios", "empregador"],
    "Users": ["pessoas", "populacao", "sindicato", "sindicatos", "equipe", "funcionarios", "brasileiros"],
    "Banknote": ["dinheiro", "salario", "salarios", "renda", "pagar", "pagamento", "reais", "real"],
    "Coins": ["custo", "custos", "preco", "imposto", "impostos", "tributo", "tributos", "taxa"],
    "TrendingUp": ["crescer", "crescimento", "aumento", "aumentar", "subir", "alta", "lucro"],
    "TrendingDown": ["queda", "cair", "reduzir", "reducao", "diminuir", "perda", "prejuizo", "crise"],
    "TriangleAlert": ["risco", "riscos", "perigo", "cuidado", "atencao", "alerta", "problema", "problemas"],
    "Vote": ["eleicao", "eleicoes", "eleitoral", "voto", "votar", "candidato"],
    "FileText": ["contrato", "contratos", "documento", "proposta", "pec", "projeto", "texto"],
    "CalendarDays": ["semana", "semanal", "dias", "domingo", "folga", "feriado", "calendario", "6x1"],
    "Lightbulb": ["ideia", "solucao", "inovacao", "estrategia", "oportunidade"],
    "Handshake": ["acordo", "negociacao", "negociar", "dialogo", "parceria", "consenso"],
    "MessageCircle": ["conversa", "debate", "discussao", "opiniao", "falar"],
    "GraduationCap": ["educacao", "escola", "estudo", "curso", "formacao", "professor"],
    "HeartPulse": ["saude", "doenca", "hospital", "bem-estar", "qualidade de vida"],
    "Globe": ["mundo", "pais", "paises", "internacional", "global", "europa"],
    "ShieldCheck": ["seguranca", "protecao", "garantia", "garantir", "proteger"],
    "Target": ["meta", "objetivo", "foco", "resultado", "resultados"],
}
UNIDADES = {
    "%": "%", "por cento": "%", "porcento": "%", "mil": " mil", "milhao": " mi", "milhoes": " mi", "bilhao": " bi",
    "bilhoes": " bi", "trilhao": " tri", "trilhoes": " tri", "reais": "", "horas": "h", "hora": "h", "anos": " anos",
    "dias": " dias", "vezes": "x",
}
ENFASE = {"nunca", "sempre", "ninguem", "todos", "tudo", "nada", "problema", "erro", "verdade", "importante", "lei",
          "proibido", "obrigatorio", "dinheiro", "custo", "risco", "milhoes", "bilhoes", "mil", "maior", "menor", "pior",
          "melhor", "fim", "crise", "nao", "jamais", "urgente", "segredo"}
INTERVALO_MIN = 5.5   # s entre o início de duas cenas
DUR_CENA = (2.6, 3.6)
MAX_CENAS = 6


@dataclass
class PlanoMotion:
    palavras: list[dict]
    cenas: list[dict] = field(default_factory=list)
    zooms: list[float] = field(default_factory=list)  # instantes de punch-in (s desde o início do corte)
    transicoes: list[float] = field(default_factory=list)


def _palavras_rel(palavras: list[Palavra], origem: float) -> list[dict]:
    saida, ultima_enfase = [], -9.0
    for p in palavras:
        n = _norm(p.texto).strip(".,!?;:…\"'")
        enf = (bool(re.search(r"\d", n)) or n in ENFASE) and p.ini - ultima_enfase > 2.5
        if enf:
            ultima_enfase = p.ini
        texto = p.texto.strip(",;:…\"'") or p.texto   # legenda sem vírgula solta; mantém ? e !
        texto = texto[:-1] if texto.endswith(".") and not texto.endswith("..") else texto
        saida.append({"t": texto.upper(), "ini": round(p.ini - origem, 3), "fim": round(p.fim - origem, 3), "enfase": enf})
    return saida


def inteiro_em(v) -> int | None:
    """Primeiro número inteiro de um valor do LLM (aceita 3, "3", "3. [12.0s] frase...")."""
    m = re.search(r"\d+", str(v))
    return int(m.group(0)) if m else None


def _escala(valor: float, sufixo: str) -> float:
    """O LLM às vezes manda 75000000 com sufixo "mi": volta para 75."""
    for suf, fator in (("mi", 1e6), ("bi", 1e9), ("tri", 1e12), ("mil", 1e3)):
        if sufixo.strip() == suf and valor >= fator:
            return round(valor / fator, 1)
    return valor


def _limpa(txt: str) -> str:
    return txt.strip(".,!?;:…\"'()")


def _rotulo(palavras: list[Palavra], i: int, n: int = 3) -> str:
    """Rótulo legível a partir das palavras originais (com acento), sem palavras vazias nas pontas."""
    ws = [_limpa(p.texto) for p in palavras[i:i + 6]]
    ws = [w for w in ws if w]
    while ws and (_norm(ws[0]) in STOP or len(ws[0]) <= 2):
        ws.pop(0)
    while ws and (_norm(ws[-1]) in STOP or len(ws[-1]) <= 2):
        ws.pop()
    rot = []
    for w in ws:
        if len(rot) >= n:
            break
        rot.append(w)
    while rot and (_norm(rot[-1]) in STOP or len(rot[-1]) <= 2):
        rot.pop()
    return " ".join(rot)


def _num(txt: str) -> float | None:
    try:
        return float(txt.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def cenas_por_regras(palavras: list[Palavra], origem: float) -> list[dict]:
    """Números, comparações e palavras-chave com ícone, direto do texto (rápido e sem modelo)."""
    cenas: list[dict] = []
    norm = [_norm(p.texto).strip(".,!?;:…\"'") for p in palavras]
    for i, w in enumerate(norm):
        t = palavras[i].ini - origem
        pct = re.fullmatch(r"(\d+(?:[.,]\d+)?)%", w)
        if pct:
            cenas.append({"tipo": "numero", "ini": t, "valor": _num(pct.group(1)), "sufixo": "%", "texto": _rotulo(palavras, i + 1)[:30]})
            continue
        if not re.fullmatch(r"\d+([.,]\d+)?", w):
            continue
        valor = _num(w)
        # comparação: "de 44 para 40", "44 para 40", "42 pra 40"
        seg = norm[i + 1:i + 4]
        if len(seg) >= 2 and seg[0] in ("para", "pra", "a") and re.fullmatch(r"\d+([.,]\d+)?", seg[1]):
            uni = UNIDADES.get(seg[2], "") if len(seg) > 2 else ""
            antes_txt = [_limpa(p.texto) for p in palavras[max(0, i - 4):i]]
            antes_txt = [x for x in antes_txt if len(x) > 2 and _norm(x) not in STOP and not x.isdigit()]
            cenas.append({"tipo": "comparacao", "ini": t, "antes": f"{w}{uni}", "depois": f"{seg[1]}{uni}",
                          "texto": " ".join(antes_txt[-2:])[:28]})
            continue
        prox = " ".join(norm[i + 1:i + 3])
        sufixo = next((v for k, v in sorted(UNIDADES.items(), key=lambda kv: -len(kv[0]))
                       if prox == k or prox.startswith(k + " ")), None)
        if sufixo is None or valor is None or (sufixo == "" and valor < 10):
            continue
        rotulo = _rotulo(palavras, i + 2)[:30]
        cenas.append({"tipo": "numero", "ini": t, "valor": valor, "sufixo": sufixo, "texto": rotulo or ""})
    for i, w in enumerate(norm):
        for icone, chaves in ICONES.items():
            if w in chaves:
                rot = _rotulo(palavras, i, 2) or _limpa(palavras[i].texto)
                cenas.append({"tipo": "icone", "ini": palavras[i].ini - origem, "icone": icone,
                              "texto": rot[:30], "_fraca": True})
    return cenas


def _espacar(cenas: list[dict], duracao: float) -> list[dict]:
    """Prioriza número/comparação/destaque sobre ícones; respeita o intervalo mínimo e a duração do corte."""
    ordem = {"destaque": 0, "comparacao": 1, "numero": 2, "icone": 3}
    escolhidas: list[dict] = []
    icones = 0
    for c in sorted(cenas, key=lambda c: (ordem.get(c["tipo"], 9), c.get("_fraca", False), c["ini"])):
        if len(escolhidas) >= MAX_CENAS or c["ini"] < 0 or c["ini"] > duracao - 2.0:
            continue
        if any(abs(c["ini"] - e["ini"]) < INTERVALO_MIN for e in escolhidas):
            continue
        if c["tipo"] == "icone":
            if icones >= 3:
                continue
            icones += 1
        escolhidas.append(c)
    escolhidas.sort(key=lambda c: c["ini"])
    for k, c in enumerate(escolhidas):
        prox = escolhidas[k + 1]["ini"] if k + 1 < len(escolhidas) else duracao
        dur = DUR_CENA[1] if c["tipo"] in ("numero", "comparacao") else DUR_CENA[0]
        c["fim"] = round(min(c["ini"] + dur, prox - 0.3, duracao - 0.2), 3)
        c["ini"] = round(max(c["ini"] - 0.15, 0.0), 3)  # entra um tiquinho antes da palavra
        c.pop("_fraca", None)
        c["texto"] = (c.get("texto") or "").upper()
    return [c for c in escolhidas if c["fim"] - c["ini"] >= 1.2]


PEDIDO_LLM = """Você é motion designer de vídeos curtos (Reels/TikTok). Abaixo, as frases de um corte com o segundo em que começam.

{frases}

Planeje animações ilustrativas que reforcem o que é dito (no máximo 4), e um título-gancho.
Tipos: "numero" (valor numérico grande que conta), "comparacao" (antes -> depois), "icone" (ícone + rótulo curto), "destaque" (2 a 4 palavras de impacto).
Ícones permitidos: {icones}.
Responda só JSON:
{{"titulo": "2 a 4 palavras que resumem o gancho", "cenas": [{{"frase": número inteiro da frase, "tipo": "...", "texto": "rótulo de até 4 palavras", "valor": número ou null, "sufixo": "% | mi | bi | h | ''", "antes": "", "depois": "", "icone": "Nome"}}]}}"""


def cenas_por_llm(llm, frases: list[tuple[float, str]]) -> tuple[str | None, list[dict]]:
    texto = "\n".join(f"{k}. [{t:.1f}s] {f}" for k, (t, f) in enumerate(frases[:18], 1))
    try:
        r = llm.create_chat_completion(
            messages=[{"role": "user", "content": PEDIDO_LLM.format(frases=texto, icones=", ".join(ICONES)) + " /no_think"}],
            response_format={"type": "json_object"}, temperature=0.2, max_tokens=420)
        bruto = r["choices"][0]["message"]["content"]
        d = json.loads(re.search(r"\{.*\}", bruto, re.S).group(0))
    except Exception:
        return None, []
    cenas = []
    for c in d.get("cenas", [])[:4]:
        try:
            k = (inteiro_em(c.get("frase")) or 0) - 1
            if not 0 <= k < len(frases):
                continue
            tipo = c.get("tipo")
            base = {"tipo": tipo, "ini": frases[k][0] + 0.4, "texto": str(c.get("texto") or "")[:32]}
            valor = _num(str(c.get("valor"))) if c.get("valor") not in (None, "") else None
            numeros_da_frase = {_num(x) for x in re.findall(r"\d+(?:[.,]\d+)?", frases[k][1])}
            if tipo == "numero" and valor is not None and (valor in numeros_da_frase
                                                         or _escala(valor, str(c.get("sufixo") or "")) in numeros_da_frase):
                suf = str(c.get("sufixo") or "")[:4]
                base.update(valor=_escala(valor, suf), sufixo=(" " + suf.strip()) if suf.strip() not in ("", "%", "h", "x") else suf.strip())
            elif tipo == "comparacao" and c.get("antes") and c.get("depois") and re.search(r"\d", frases[k][1]):
                base.update(antes=str(c["antes"])[:8], depois=str(c["depois"])[:8])
            elif tipo == "icone" and c.get("icone") in ICONES:
                base.update(icone=c["icone"])
            elif tipo == "destaque" and base["texto"]:
                pass
            else:
                continue
            cenas.append(base)
        except (TypeError, ValueError):
            continue
    titulo = str(d.get("titulo") or "").strip()[:32] or None
    return titulo, cenas


def planejar(trechos: list[tuple[float, float, list[Palavra]]], llm=None, log=None) -> PlanoMotion:
    """Plano de um corte formado por 1+ trechos do vídeo (ex.: gancho "cold open" + corpo).

    `trechos`: (início no vídeo, fim no vídeo, palavras). Os tempos do plano são do corte montado (trechos em sequência)."""
    palavras_rel: list[dict] = []
    cenas: list[dict] = []
    transicoes: list[float] = []
    frases: list[tuple[float, str]] = []
    deslocamento = 0.0
    for k, (ini, fim, ws) in enumerate(trechos):
        origem = ini - deslocamento
        palavras_rel += _palavras_rel(ws, origem)
        cenas += cenas_por_regras(ws, origem)
        atual: list[str] = []
        ini_frase = (ws[0].ini - origem) if ws else deslocamento
        for p in ws:
            atual.append(p.texto)
            if p.texto.endswith((".", "?", "!")):
                frases.append((ini_frase, " ".join(atual)))
                atual, ini_frase = [], p.fim - origem
        if atual:
            frases.append((ini_frase, " ".join(atual)))
        deslocamento += fim - ini
        if k + 1 < len(trechos):
            transicoes.append(round(deslocamento, 3))
    duracao = deslocamento
    if llm is not None:
        titulo, extra = cenas_por_llm(llm, frases)
        if log:
            log(f"Motion: LLM sugeriu {len(extra)} cena(s)" + (f" e o título “{titulo}”" if titulo else ""))
        cenas = extra + cenas
        if titulo and not transicoes:
            cenas.append({"tipo": "destaque", "ini": 0.35, "texto": titulo})
    escolhidas = _espacar(cenas, duracao)
    zooms = [c["ini"] + 0.1 for c in escolhidas if c["tipo"] in ("numero", "comparacao", "destaque")]
    zooms += [p["ini"] for p in palavras_rel if p["enfase"]]
    zooms_finais: list[float] = []
    for z in sorted(zooms):
        if z > 0.5 and z < duracao - 2 and all(abs(z - y) > 6.0 for y in zooms_finais):
            zooms_finais.append(round(z, 3))
    if log:
        log(f"Motion: {len(escolhidas)} ilustração(ões), {len(zooms_finais)} zoom(s) de ênfase, {len(transicoes)} transição(ões)")
    return PlanoMotion(palavras_rel, escolhidas, zooms_finais[:6], transicoes)
