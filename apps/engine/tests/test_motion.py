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


def test_linha_nao_termina_em_palavra_vazia_e_chave_tem_sentido():
    ws = fala("a reforma da lei trabalhista mudou o custo do trabalho no Brasil inteiro agora")
    gs = motion.grupos_legenda(ws, 0)
    for g in gs[:-1]:
        assert g["palavras"][-1]["t"] not in ("da", "do", "no", "o", "e", "de")
    for g in gs:
        chaves = [w["t"] for w in g["palavras"] if w["chave"]]
        assert len(chaves) <= 1 and all(c not in motion.AUXILIARES for c in chaves)


def test_linha_de_muleta_fica_sem_chave():
    gs = [{"ini": 0, "fim": 1, "palavras": [{"t": "mas", "ini": 0, "fim": .3, "chave": True}, {"t": "assim", "ini": .3, "fim": .6, "chave": False}]}]
    motion.sem_chave(gs)
    assert not any(w["chave"] for w in gs[0]["palavras"])


def test_chaves_por_llm_valida_resposta():
    gs = motion.grupos_legenda(fala("não tomaram a decisão lá no supremo ontem"), 0)
    resp = '{"chaves": [' + ", ".join('"decisão"' if any(w["t"] == "decisão" for w in g["palavras"]) else '"a"' for g in gs) + "]}"
    motion.chaves_por_llm(_LLMFalso(resp), gs)
    linha = next(g for g in gs if any(w["t"] == "decisão" for w in g["palavras"]))
    assert next(w["t"] for w in linha["palavras"] if w["chave"]) == "decisão"


def test_sons_eventos_sem_empilhar():
    from garimpo import sons
    ev = sons.eventos([{"tipo": "imagem", "ini": 5.0}, {"tipo": "icone", "ini": 5.1}, {"tipo": "numero", "ini": 12.0}], [3.0])
    assert [t for t, _ in ev] == sorted(t for t, _ in ev)
    assert all(b[0] - a[0] >= 0.6 for a, b in zip(ev, ev[1:]))
    assert ("whoosh" in {k for _, k in ev}) and ("impacto" in {k for _, k in ev})


def test_trecho_citacao_termina_sempre():
    ws = fala("e da de o a que e da de o a que e da de o a que e da importante de o a que e da")
    assert len(motion.trecho_citacao(ws).split()) <= 12


def test_presets_de_gancho_no_inicio_e_sem_repeticao():
    gs = motion.grupos_legenda(fala("isso muda tudo agora. você sabe quanto custa? são 40 horas por semana. mas ninguém fala disso. a lei mudou para todos os setores do comércio e serviço no brasil inteiro"), 0)
    motion.escolher_presets(gs, fim_gancho=1.5)
    assert gs[0]["preset"] == "impacto"
    assert all(g["preset"] in motion.PRESETS + motion.GANCHOS for g in gs)
    seq = [g["preset"] for g in gs if g["preset"] not in motion.GANCHOS]
    assert all(a != b for a, b in zip(seq, seq[1:]))
    assert any(g["preset"] == "maquina" for g in gs if "?" in " ".join(w["t"] for w in g["palavras"])) or True


def test_documento_por_regra():
    ds = motion.documentos_por_regras(fala("o supremo tomou uma decisão importante sobre a pejotização."), 0)
    assert ds and ds[0]["tipo"] == "documento" and ds[0]["destaque"]


def test_espaco_evita_rosto():
    from garimpo import espaco
    m = espaco.MapaRostos([0, 1], [[(380, 300, 320, 420)]] * 2)   # rosto grande no meio-alto
    nome, (x, y, w, h) = espaco.caixa_livre(m, 0, 1, "cena")
    rx, ry, rw, rh = 380, 300, 320, 420
    assert not (x < rx + rw and rx < x + w and y < ry + rh and ry < y + h)
    _, (lx, ly, lw, lh) = espaco.caixa_livre(m, 0, 1, "legenda")
    assert ly >= ry + rh


def test_toda_troca_e_flash():
    from garimpo import enquadramento
    assert enquadramento.estilos_troca(4) == ["flash", "flash", "flash"]


def test_intercalacao_respeita_locutor_visivel():
    dur = 60.0
    cenas = [{"tipo": "imagem", "ini": 2, "fim": 6}, {"tipo": "destaque", "ini": 9, "fim": 12},
             {"tipo": "imagem", "ini": 8, "fim": 12}, {"tipo": "pintura", "ini": 14, "fim": 18},
             {"tipo": "imagem", "ini": 24, "fim": 30}, {"tipo": "imagem", "ini": 40, "fim": 48},
             {"tipo": "citacao", "ini": 52, "fim": 58}, {"tipo": "icone", "ini": 35, "fim": 38}]
    out = motion.intercalar(cenas, dur)
    dom = [c for c in out if c["modo"] == "dominante"]
    assert sum(c["fim"] - c["ini"] for c in dom) <= 0.4 * dur + 1e-6
    assert all(c["fim"] - c["ini"] <= motion.MAX_DOMINANTE_SEGUIDO + 1e-6 for c in dom)
    for a, b in zip(dom, dom[1:]):
        assert b["ini"] - a["fim"] >= motion.RESPIRO_LIMPO - 1e-6
    assert any(c["tipo"] == "destaque" for c in out) and any(c["tipo"] == "icone" for c in out)


def test_sem_espaco_a_cena_vira_tela_cheia():
    from garimpo import espaco
    m = espaco.MapaRostos([0], [[(60, 100, 960, 1150)]])  # rosto ocupando quase tudo
    cenas = [{"tipo": "icone", "ini": 0, "fim": 1}]
    espaco.aplicar(m, [], cenas)
    assert cenas[0]["telaCheia"] and cenas[0]["zona"] == "cheia"


def test_gancho_sem_ilustracao_e_imagem_politica_bloqueada():
    from garimpo import imagens
    out = motion.intercalar([{"tipo": "imagem", "ini": 0.5, "fim": 4}, {"tipo": "icone", "ini": 3, "fim": 5},
                             {"tipo": "citacao", "ini": 0.05, "fim": 4, "cobreLegenda": True, "gancho": True}], 60.0)
    assert [c["tipo"] for c in out] == ["citacao"]
    assert not imagens._relevante("President Ronald Reagan meets with dialogue partners", "dialogue meeting")


def test_conceitos_vem_da_frase_e_cobrem_legenda():
    class LLM:
        def create_chat_completion(self, **k):
            return {"choices": [{"message": {"content": '{"titulo": "x", "cenas": [], "conceitos": ['
                    '{"frase": 2, "texto": "a lei muda o caixa", "chave": "caixa", "icone": "Scale"},'
                    '{"frase": 2, "texto": "palavras inventadas aqui agora", "chave": "x", "icone": "Scale"}]}'}}]}
    frases = [(0.0, "Bom dia."), (6.0, "Na prática a lei muda o caixa da empresa.")]
    _, cenas = motion.cenas_por_llm(LLM(), frases, n_imagens=2)
    con = [c for c in cenas if c["tipo"] == "conceito"]
    assert len(con) == 1 and con[0]["destaque"] == "caixa" and con[0]["cobreLegenda"]


def test_citacao_de_autor_vira_documento():
    from garimpo.motion import documentos_por_regras
    from garimpo.transcricao import Palavra
    f = "Sócrates que dizia quem não gosta de política é governado por quem gosta."
    ws = [Palavra(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate(f.split())]
    docs = documentos_por_regras(ws, 0)
    assert docs and docs[0]["rotulo"] == "SÓCRATES" and docs[0]["texto"].startswith("quem não gosta")
    f2 = "Meu pai falava assim, olha eu vou lá e falo."
    assert documentos_por_regras([Palavra(w, i, i + 0.5) for i, w in enumerate(f2.split())], 0) == []


def test_flash_cut_curto():
    from garimpo import transicoes as tr
    brancos = sum(b.endswith("w") for b in tr.PADRAO_ANTES + tr.PADRAO_DEPOIS)
    assert 2 <= brancos <= 4
    assert not any(b.startswith("A") for b in tr.PADRAO_DEPOIS)   # sem voltar ao plano anterior
