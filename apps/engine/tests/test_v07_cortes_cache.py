"""v0.7: fechamento sem cortar a fala, cache global da transcrição e refino de tempos."""
import json

import numpy as np

from garimpo import cache, cortes, transcricao
from garimpo.modelos import Corte, Frase, Palavra


def frase(texto, ini, dur=10.0):
    ps = texto.split()
    passo = dur / len(ps)
    return Frase([Palavra(t, ini + i * passo, ini + (i + 1) * passo) for i, t in enumerate(ps)])


def test_nao_fecha_com_fala_emendada():
    a = frase("A lei mudou tudo para o pequeno empresário.", 0, 6)
    colada = frase("Não, e meu pai falava assim.", 6.02, 3)          # outra pessoa já falando
    assert not cortes.fecha_bem(a, colada)


def test_nao_fecha_antes_de_porem():
    a = frase("O projeto estava numa gaveta.", 0, 4)
    b = frase("Porém, a política tem uma questão de tempo.", 4.5, 4)
    assert not cortes.fecha_bem(a, b)
    longe = frase("Porém, mudando de assunto completamente.", 6.0, 4)  # pausa longa: pode fechar
    assert cortes.fecha_bem(a, longe)


def test_fecha_com_pausa_e_frase_nova():
    a = frase("No fim, quem paga a conta é o consumidor.", 0, 5)
    b = frase("Agora vamos falar de outro ponto.", 5.8, 3)
    c = frase("Outro assunto começa aqui com calma.", 5.8, 3)
    assert not cortes.fecha_bem(a, b)       # "agora" retoma
    assert cortes.fecha_bem(a, c)
    assert not cortes.fecha_bem(frase("e aí a gente viu que", 0, 3), c)  # sem ponto final


def test_completar_contexto_avanca_ate_fechar():
    fs = [frase(f"Frase de conteúdo número {i} sobre o tema.", i * 9.0, 8.2) for i in range(8)]
    fs[4] = frase("Mas isso ainda não acabou aqui.", 36.0, 8.2)   # continua a ideia da 3
    c = cortes.completar_contexto(Corte("t", fs[:4], 1.0), fs)
    assert c.frases[-1] is fs[4]


def test_cache_da_transcricao_reaproveita(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTO_DADOS", str(tmp_path / "dados"))
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 5000)
    k = cache.chave_transcricao(video, "large-v3-turbo", ["Sindeprestem"])
    assert cache.ler_json("transcricoes", k) is None
    cache.gravar_json("transcricoes", k, {"fps": 30, "palavras": []})
    # mesmo conteúdo em outro caminho/projeto = mesma chave
    copia = tmp_path / "outra" / "copia.mp4"
    copia.parent.mkdir()
    copia.write_bytes(video.read_bytes())
    import os
    os.utime(copia, (video.stat().st_atime, video.stat().st_mtime))
    assert cache.chave_transcricao(copia, "large-v3-turbo", ["Sindeprestem"]) == k
    assert cache.ler_json("transcricoes", k) == {"fps": 30, "palavras": []}
    # dicionário diferente ou outro modelo = outra chave
    assert cache.chave_transcricao(video, "large-v3-turbo", []) != k
    assert cache.chave_transcricao(video, "small", ["Sindeprestem"]) != k


def test_pipeline_pula_transcricao_com_cache(tmp_path, monkeypatch):
    from garimpo import midia, pipeline
    monkeypatch.setenv("ATTO_DADOS", str(tmp_path / "dados"))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    video = tmp_path / "v.mp4"
    video.write_bytes(b"y" * 3000)
    monkeypatch.setattr(midia, "informacoes", lambda v: {"fps": 30.0, "largura": 1920, "altura": 1080})
    monkeypatch.setattr(midia, "extrair_wav", lambda v, w: w.write_bytes(b""))
    chamadas = []
    monkeypatch.setattr(transcricao, "transcrever", lambda *a, **k: chamadas.append(1) or [Palavra("Olá.", 0, 1)])
    p1, p2 = tmp_path / "proj1", tmp_path / "proj2"
    pipeline.transcrever(video, p1, "large-v3-turbo")
    pipeline.transcrever(video, p2, "large-v3-turbo")      # projeto novo, mesmo vídeo
    assert len(chamadas) == 1
    assert json.loads((p2 / "transcricao.json").read_text(encoding="utf-8"))["palavras"][0]["texto"] == "Olá."
    pipeline.transcrever(video, tmp_path / "proj3", "large-v3-turbo", refazer=True)
    assert len(chamadas) == 2


def test_refinar_tempos_puxa_fim_para_onde_a_voz_acaba():
    sr = 16000
    x = np.zeros(sr * 3, dtype=np.int16)
    x[int(0.5 * sr):int(1.4 * sr)] = (8000 * np.sin(np.arange(int(0.9 * sr)) * 0.3)).astype(np.int16)  # voz 0,5-1,4 s
    ws = [Palavra("palavra.", 0.55, 1.15), Palavra("Outra", 2.2, 2.6)]                   # Whisper cortou cedo
    transcricao.refinar_tempos(ws, {"sr": sr, "x": x}, 30.0)
    assert abs(ws[0].fim - 1.4) < 0.05
    assert abs(ws[0].ini - 0.5) < 0.05
