from garimpo import juiz, motion
from garimpo.modelos import Palavra


def fala(texto, ini=0.0, passo=0.4):
    return [Palavra(t, ini + i * passo, ini + i * passo + passo * 0.9) for i, t in enumerate(texto.split())]


def test_regras_acham_numero_comparacao_e_percentual():
    ws = fala("São 75 milhões de pessoas, a jornada cai de 44 para 40 horas e 30% das empresas sofrem.")
    tipos = {(c["tipo"], c.get("sufixo"), c.get("antes"), c.get("depois")) for c in motion.cenas_por_regras(ws, 0)}
    assert ("numero", " mi", None, None) in tipos
    assert ("comparacao", None, "44h", "40h") in tipos
    assert ("numero", "%", None, None) in tipos


def test_plano_espacado_dentro_do_corte_e_com_zoom():
    ws = fala("A lei mudou. São 75 milhões de pessoas. " + "conteúdo " * 40 + "e a jornada cai de 44 para 40 horas.")
    p = motion.planejar([(0.0, ws[-1].fim + 0.2, ws)])
    dur = ws[-1].fim + 0.2
    assert p.cenas and all(0 <= c["ini"] < c["fim"] <= dur for c in p.cenas)
    inis = [c["ini"] for c in p.cenas]
    assert all(b - a >= motion.INTERVALO_MIN - 0.2 for a, b in zip(inis, inis[1:]))
    assert p.zooms and not p.transicoes


def test_cold_open_gera_transicao_e_tempos_em_sequencia():
    gancho = fala("Isso vai custar 2 bilhões.", 100.0)
    corpo = fala("A reforma começou em março e mudou tudo para o setor.", 50.0)
    p = motion.planejar([(99.9, gancho[-1].fim + 0.1, gancho), (49.9, corpo[-1].fim + 0.1, corpo)])
    assert len(p.transicoes) == 1
    t = p.transicoes[0]
    corpo_rel = [w for w in p.palavras if w["t"] == "REFORMA"][0]
    assert corpo_rel["ini"] > t  # o corpo vem depois do gancho


def test_legenda_sem_virgula_e_maiuscula():
    ps = motion._palavras_rel(fala("Olá, mundo. Tudo bem?"), 0)
    assert [p["t"] for p in ps] == ["OLÁ", "MUNDO", "TUDO", "BEM?"]


def test_leitura_tolerante_do_llm():
    assert motion.inteiro_em("3. [9.0s] São 75 milhões") == 3
    assert motion._escala(75_000_000, "mi") == 75
    assert juiz._num("8/10") == 8 and juiz._num(None) == 5


class _LLMFalso:
    def __init__(self, resposta):
        self.resposta = resposta

    def create_chat_completion(self, **_):
        return {"choices": [{"message": {"content": self.resposta}}]}


def test_llm_nao_inventa_numero():
    frases = [(0.0, "Foi uma decisão do Supremo."), (4.0, "São 75 milhões de pessoas.")]
    resp = ('{"titulo": "x", "cenas": [{"frase": 1, "tipo": "numero", "valor": 1, "sufixo": "mi", "texto": "decisão"},'
            '{"frase": "2. [4.0s] São", "tipo": "numero", "valor": 75000000, "sufixo": "mi", "texto": "pessoas"}]}')
    _, cenas = motion.cenas_por_llm(_LLMFalso(resp), frases)
    assert [c["valor"] for c in cenas] == [75]
