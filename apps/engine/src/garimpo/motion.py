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
# Consultas no acervo do Met (Open Access) por tema; testadas para trazer pinturas em domínio público pertinentes.
PINTURAS = {
    "Briefcase": "harvest workers", "Building2": "factory", "Users": "crowd street", "Banknote": "wall street",
    "Coins": "wall street", "TrendingDown": "storm sea", "TriangleAlert": "shipwreck storm", "Landmark": "town hall assembly",
    "Scale": "allegory prudence", "Clock": "laborers", "CalendarDays": "harvesters", "Vote": "town hall assembly",
    "Handshake": "treaty", "Globe": "ships harbor", "TrendingUp": "harvesters", "FileText": "letter reading",
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
    grupos: list[dict] = field(default_factory=list)
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


MAX_GRUPO = 5


def _peso_chave(texto: str) -> float:
    n = _norm(_limpa(texto))
    if not n:
        return -9
    p = 0.0
    if re.search(r"\d", n):
        p += 3
    if n in ENFASE:
        p += 2
    if n not in STOP and len(n) >= 4:
        p += 1 + len(n) / 10
    return p


def grupos_legenda(ws: list[Palavra], origem: float) -> list[dict]:
    """Legenda em linhas de até 5 palavras (como na referência). Em cada linha, a palavra mais importante é a
    "chave" (grande, serifada itálica, no centro); as demais ficam pequenas acima/abaixo, em minúsculas."""
    grupos: list[list[Palavra]] = [[]]
    for k, p in enumerate(ws):
        grupos[-1].append(p)
        prox = ws[k + 1] if k + 1 < len(ws) else None
        if prox is None:
            break
        quebra = (len(grupos[-1]) >= MAX_GRUPO or p.texto.endswith((".", "?", "!", ",", ";", ":"))
                  or prox.ini - p.fim > 0.35)
        if quebra and len(grupos[-1]) >= 2 or prox.ini - p.fim > 0.8:
            # não termina a linha em palavra vazia ("no", "e", "da"): ela passa para a próxima linha
            pendente = []
            while len(grupos[-1]) > 2 and _norm(_limpa(grupos[-1][-1].texto)) in STOP and not grupos[-1][-1].texto.endswith((".", "?", "!", ",")):
                pendente.insert(0, grupos[-1].pop())
            grupos.append(pendente)
    saida = []
    for g in grupos:
        if not g:
            continue
        chave = max(range(len(g)), key=lambda i: _peso_chave(g[i].texto))
        palavras = []
        for i, p in enumerate(g):
            t = _limpa(p.texto).lower() or p.texto.lower()
            palavras.append({"t": t, "ini": round(p.ini - origem, 3), "fim": round(p.fim - origem, 3), "chave": i == chave})
        saida.append({"ini": palavras[0]["ini"], "fim": palavras[-1]["fim"], "palavras": palavras})
    for a, b in zip(saida, saida[1:]):
        a["fim"] = round(min(b["ini"] - 0.02, a["fim"] + 0.6), 3)   # a linha fica até a próxima (respiro curto)
    if saida:
        saida[-1]["fim"] = round(saida[-1]["fim"] + 0.5, 3)
    return saida


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
    ordem = {"citacao": 0, "destaque": 1, "comparacao": 2, "numero": 3, "icone": 4}
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
        dur = {"numero": 3.4, "comparacao": 3.6, "citacao": 3.8, "pintura": 3.0}.get(c["tipo"], 2.8)
        c["fim"] = round(min(c["ini"] + dur, prox - 0.3, duracao - 0.2), 3)
        c["ini"] = round(max(c["ini"] - 0.15, 0.0), 3)  # entra um tiquinho antes da palavra
        c.pop("_fraca", None)
        c["texto"] = (c.get("texto") or "").strip()
    return [c for c in escolhidas if c["fim"] - c["ini"] >= 1.2]


PEDIDO_LLM = """Você é motion designer de vídeos curtos (Reels/TikTok). Abaixo, as frases de um corte com o segundo em que começam.

{frases}

Planeje animações ilustrativas que reforcem o que é dito (no máximo 4), e um título-gancho.
Tipos: "numero" (valor numérico que aparece na fala), "comparacao" (antes -> depois), "icone" (ícone + rótulo curto), "destaque" (2 a 4 palavras de impacto), "citacao" (a frase mais forte, até 10 palavras, literal).
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
            base = {"tipo": tipo, "ini": frases[k][0] + 0.4, "texto": str(c.get("texto") or "")[:40]}
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
            elif tipo == "citacao" and base["texto"]:
                base["texto"] = str(c.get("texto"))[:80]
            else:
                continue
            cenas.append(base)
        except (TypeError, ValueError):
            continue
    titulo = str(d.get("titulo") or "").strip()[:32] or None
    return titulo, cenas


def trecho_citacao(ws: list[Palavra], maximo: int = 9) -> str:
    """Até `maximo` palavras em volta da palavra mais forte (a citação é lida de relance)."""
    textos = [_limpa(p.texto) for p in ws if _limpa(p.texto)]
    if len(textos) <= maximo:
        return " ".join(textos)
    centro = max(range(len(textos)), key=lambda i: _peso_chave(textos[i]))
    ini = max(0, min(centro - maximo // 2, len(textos) - maximo))
    while ini > 0 and _norm(textos[ini]) in STOP:   # não começa em "da", "e"...
        ini += 1 if ini + maximo < len(textos) else -1
        if ini <= 0:
            break
    trecho = textos[ini:ini + maximo]
    while trecho and _norm(trecho[-1]) in STOP:
        trecho.pop()
    return ("… " if ini > 0 else "") + " ".join(trecho) + (" …" if ini + maximo < len(textos) else "")


def _imagem_data_uri(arq) -> str:
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(arq.read_bytes()).decode("ascii")


def com_pinturas(cenas: list[dict], duracao: float, log=None, maximo: int | None = None) -> list[dict]:
    """Troca 1 ícone (2 em cortes longos) por uma pintura em domínio público do tema (b-roll em tela cheia)."""
    from . import recursos
    maximo = maximo if maximo is not None else (2 if duracao > 55 else 1)
    usados: set[int] = set()
    consultas_usadas: set[str] = set()
    feitas = 0
    for c in cenas:
        if feitas >= maximo:
            break
        consulta = PINTURAS.get(c.get("icone", ""))
        if c["tipo"] != "icone" or not consulta or consulta in consultas_usadas:
            continue
        consultas_usadas.add(consulta)
        r = recursos.pintura(consulta, usados, log)
        if not r:
            continue
        arq, credito = r
        c.update(tipo="pintura", img=_imagem_data_uri(arq), credito=credito)
        c["fim"] = round(min(c["ini"] + 3.0, duracao - 0.2), 3)
        feitas += 1
    return cenas


def planejar(trechos: list[tuple[float, float, list[Palavra]]], llm=None, log=None, pinturas: bool = True) -> PlanoMotion:
    """Plano de um corte formado por 1+ trechos do vídeo (ex.: gancho "cold open" + corpo).

    `trechos`: (início no vídeo, fim no vídeo, palavras). Os tempos do plano são do corte montado (trechos em sequência)."""
    palavras_rel: list[dict] = []
    grupos: list[dict] = []
    cenas: list[dict] = []
    citacao: dict | None = None
    transicoes: list[float] = []
    frases: list[tuple[float, str]] = []
    deslocamento = 0.0
    for k, (ini, fim, ws) in enumerate(trechos):
        origem = ini - deslocamento
        palavras_rel += _palavras_rel(ws, origem)
        grupos += grupos_legenda(ws, origem)
        if k == 0 and len(trechos) > 1 and ws:
            # cold open: a frase de impacto aparece como citação em destaque (aspas, texto escrito no centro)
            citacao = {"tipo": "citacao", "ini": 0.05, "fim": round(fim - ini - 0.05, 3),
                       "texto": trecho_citacao(ws), "cobreLegenda": True}
        else:
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
    if citacao:
        inicio_corpo = transicoes[0] if transicoes else 0
        cenas = [c for c in cenas if c["ini"] > inicio_corpo + 1.0]
    escolhidas = _espacar(cenas, duracao)
    if pinturas:
        escolhidas = com_pinturas(escolhidas, duracao, log)
    if citacao:
        escolhidas = [citacao] + escolhidas
    zooms = [c["ini"] + 0.1 for c in escolhidas if c["tipo"] in ("numero", "comparacao", "destaque", "icone")]
    zooms += [p["ini"] for p in palavras_rel if p["enfase"]]
    zooms_finais: list[float] = []
    for z in sorted(zooms):
        if z > 0.5 and z < duracao - 2 and all(abs(z - y) > 6.0 for y in zooms_finais):
            zooms_finais.append(round(z, 3))
    if log:
        log(f"Motion: {len(escolhidas)} ilustração(ões), {len(zooms_finais)} zoom(s) de ênfase, {len(transicoes)} transição(ões)")
    return PlanoMotion(palavras_rel, grupos, escolhidas, zooms_finais[:6], transicoes)
