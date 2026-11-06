import numpy as np

from garimpo import cortes
from garimpo.modelos import Corte, Frase, Palavra


def frase(texto, ini, dur=10.0):
    ps = texto.split()
    passo = dur / len(ps)
    return Frase([Palavra(t, ini + i * passo, ini + (i + 1) * passo) for i, t in enumerate(ps)])


def test_detecta_ruido_de_gravacao():
    assert cortes.e_ruido(frase("Um, dois, três, gravando.", 0, 3))
    assert cortes.e_ruido(frase("1, 2, 3 testando o som", 0, 3))
    assert not cortes.e_ruido(frase("O contrato vale por três anos.", 0, 4))


def test_corte_nao_pega_o_teste_de_som_do_inicio():
    from garimpo.modelos import Tema
    fs = [frase("Um dois três gravando.", 0, 3)] + [frase(f"Conteúdo importante número {i} da conversa de hoje.", 5 + i * 10) for i in range(8)]
    t = Tema("x", [type("P", (), {"frases": fs, "ini": fs[0].ini, "fim": fs[-1].fim})()])
    cs = cortes.candidatos(t, cortes._idf(fs), 1e9, 0.0)
    assert cs and all(not any(cortes.e_ruido(f) for f in c.frases) for c in cs)


def test_frase_dependente_puxa_a_anterior():
    ant = frase("A regra mudou em 2024 para todos os sindicatos.", 0, 8)
    dep = frase("Isso significa que ninguém mais precisa pagar a taxa.", 8.5, 8)
    resto = [frase(f"E por isso o tema é importante {i} para todos.", 17 + i * 9, 8) for i in range(4)]
    todas = [ant, dep] + resto
    c = cortes.completar_contexto(Corte("t", [dep] + resto[:3], 1.0), todas)
    assert c.frases[0] is ant


def test_fim_em_frase_completa():
    a = frase("Primeira parte da ideia", 0, 20)          # sem pontuação final
    b = frase("que termina aqui.", 20.5, 5)
    c = cortes.completar_contexto(Corte("t", [a], 1.0), [a, b])
    assert c.frases[-1] is b


def test_limites_vao_para_o_silencio():
    sr = 16000
    x = np.zeros(sr * 4, dtype=np.int16)
    x[int(1.0 * sr):int(2.0 * sr)] = 8000   # "palavra" de 1.0 a 2.0 s; silêncio ao redor
    wav = {"sr": sr, "x": x}
    ini, fim = cortes.ajustar_limites(1.05, 1.95, None, None, wav)   # tempos do Whisper meio errados (dentro da palavra)
    assert ini <= 1.0 - 0.0 and fim >= 2.0     # não corta a palavra
