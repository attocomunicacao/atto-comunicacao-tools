from garimpo import cortes, estrutura, legenda
from garimpo.modelos import Palavra


def fala(inicio: float, palavras: list[str], passo: float = 0.4) -> list[Palavra]:
    return [Palavra(w, inicio + i * passo, inicio + i * passo + 0.3) for i, w in enumerate(palavras)]


def test_frases_por_pontuacao_e_pausa():
    p = fala(0, ["Olá", "pessoal."]) + fala(1.0, ["Vamos", "começar"]) + fala(5.0, ["Depois", "falamos."])
    fs = estrutura.frases(p)
    assert [f.texto for f in fs] == ["Olá pessoal.", "Vamos começar", "Depois falamos."]


def _discurso():
    palavras, t = [], 0.0
    blocos = [
        "contrato trabalho jornada escala sindicato negociação coletiva acordo jornada escala trabalho.",
        "futebol campeonato gol torcida estádio jogo time treinador campeonato gol torcida.",
    ]
    for bloco in blocos:
        for _ in range(8):  # 8 parágrafos por assunto
            for _ in range(3):  # 3 frases de ~11 palavras (~4,4 s cada)
                ps = fala(t, bloco.split())
                palavras += ps
                t = ps[-1].fim + 0.3
            t += 2.0  # pausa de parágrafo
    return palavras


def test_temas_e_cortes_respeitam_limites():
    ps = estrutura.paragrafos(estrutura.frases(_discurso()))
    ts = estrutura.temas(ps)
    assert len(ts) >= 2
    cs = cortes.sugerir(ts)
    assert cs
    for c in cs:
        assert cortes.MIN_S <= c.duracao <= cortes.MAX_S
        assert c.texto.rstrip().endswith(".")  # termina em frase completa


def test_legenda_ass_maiuscula_e_palavra_a_palavra(tmp_path):
    from garimpo.modelos import Corte, Frase

    c = Corte("t", [Frase(fala(10.0, ["olá", "mundo", "bonito"]))], 1.0)
    ass = legenda.gerar_ass(c, tmp_path / "a.ass").read_text(encoding="utf-8")
    assert ass.count("Dialogue:") == 3
    assert "OLÁ" in ass and "olá" not in ass and "Lato" in ass
