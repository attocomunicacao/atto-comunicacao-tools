import re

from garimpo import enquadramento as e, legenda
from garimpo.modelos import Corte, Frase, Palavra


def test_geometria_16x9():
    assert e.geometria(1920, 1080) == (606, 1214)


def test_um_rosto_vira_recorte_unico_centrado():
    segs = e.segmentar([("unico", [1400.0])] * 20, 5.0, 1920, 1080)
    assert len(segs) == 1 and segs[0].modo == "unico"
    assert abs(segs[0].centros[0] - 1400) < 1


def test_dois_rostos_dividem_a_tela_esquerda_em_cima():
    r = [e.Rosto(1300, 400, 120, 160), e.Rosto(500, 400, 118, 158)]
    assert e._escolher(r, 1920) == ("dividido", [500, 1300])


def test_rosto_ao_fundo_e_ignorado_e_painel_escolhe_quem_fala():
    fundo = [e.Rosto(500, 300, 40, 50), e.Rosto(1300, 400, 150, 190)]
    assert e._escolher(fundo, 1920) == ("unico", [1300])
    painel = [e.Rosto(300, 400, 100, 130, 1.0), e.Rosto(900, 400, 100, 130, 9.0), e.Rosto(1500, 400, 100, 130, 2.0)]
    assert e._escolher(painel, 1920) == ("unico", [900])


def test_troca_so_vale_se_durar_e_ruido_e_ignorado():
    a, b = ("unico", [500.0]), ("unico", [1500.0])
    ruido = e.segmentar([a] * 8 + [b] + [a] * 8, 4.25, 1920, 1080)
    assert len(ruido) == 1
    troca = e.segmentar([a] * 8 + [b] * 8, 4.0, 1920, 1080)
    assert [round(s.fim, 2) for s in troca] == [2.0, 4.0] and troca[1].centros == [1500.0]


def test_pequena_variacao_do_rosto_nao_mexe_no_eixo():
    tremida = [("unico", [900.0 + (i % 5) * 20]) for i in range(40)]
    segs = e.segmentar(tremida, 10.0, 1920, 1080)
    assert len(segs) == 1


def test_rosto_que_pisca_nao_vira_tela_dividida():
    base = [("unico", [900.0])] * 12 + [("dividido", [500.0, 1300.0])] * 2 + [("unico", [900.0])] * 12
    assert len(e.segmentar(base, 6.5, 1920, 1080)) == 1


def test_filtro_divide_em_960_exatos():
    f = e.filtro([e.Segmento(0, 2, "dividido", [500, 1300])], 1920, 1080)
    assert "scale=1080:960" in f and "vstack" in f
    g = e.filtro([e.Segmento(0, 1, "unico", [900]), e.Segmento(1, 2, "unico", [1500])], 1920, 1080)
    assert "xfade=transition=fade" in g and "scale=1080:1920" in g


def test_legenda_64px_branca_sem_traco_com_glow_e_entrada_suave(tmp_path):
    ws = [Palavra("olá", 1.0, 1.6), Palavra("mundo", 1.6, 2.2)]
    ass = legenda.gerar_ass(Corte("t", [Frase(ws)], 1.0), tmp_path / "c.ass").read_text(encoding="utf-8")
    assert "Lato,64,&H00FFFFFF" in ass and ",1,0,0,5," in ass  # sem contorno nem sombra do estilo, centralizada
    assert "OLÁ" in ass and "MUNDO" in ass and "olá" not in ass
    # a entrada começa 100 px acima e termina em y=1400, em muitos quadros (easing), e a opacidade sobe
    ys = [float(x) for x in re.findall(r"[\\]pos\(540,([\d.]+)\)", ass)]
    assert min(ys) < 1310 and 1400.0 in ys and len(ys) > 30
    # saída: a palavra que dá lugar à próxima desce um pouco, desfoca e some (motion da referência)
    assert max(ys) > 1400
    ultimo = ass.splitlines()[-1]
    assert "blur" in ass and "&H00&" in ultimo  # no fim, totalmente visível
    # glow fixo: duas camadas desfocadas atrás da camada nítida (layer 2)
    assert {l.split(",")[0] for l in ass.splitlines() if l.startswith("Dialogue")} == {"Dialogue: 0", "Dialogue: 1", "Dialogue: 2"}


def test_legenda_usa_a_origem_do_corte(tmp_path):
    ws = [Palavra("oi", 10.5, 11.0)]
    ass = legenda.gerar_ass(Corte("t", [Frase(ws)], 1.0), tmp_path / "c.ass", origem=10.0).read_text(encoding="utf-8")
    assert "Dialogue: 2,0:00:00.50" in ass


def test_concat_de_modos_diferentes_com_pixel_nao_quadrado(tmp_path):
    """Regressão: fonte com SAR 404:405 fazia o concat falhar ('Failed to configure output pad')."""
    import subprocess
    from garimpo import midia
    v = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=3",
                    "-vf", "setsar=404/405", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(v)], check=True)
    segs = [e.Segmento(0, 1, "unico", [900]), e.Segmento(1, 2, "dividido", [500, 1300]),
            e.Segmento(2, 3, "unico", [1500])]
    comp = e.filtro(segs, 1920, 1080)
    saida = tmp_path / "o.mp4"
    midia._rodar(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-filter_complex", comp, "-map", "[cv]", str(saida)])
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,sample_aspect_ratio",
                        "-of", "csv=p=0", str(saida)], capture_output=True, text=True)
    assert r.stdout.strip().startswith("1080,1920,1:1")
