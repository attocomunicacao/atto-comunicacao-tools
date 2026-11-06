from garimpo.correcao.corretor import aplicar, sugerir
from garimpo.correcao.dicionario import Dicionario


def dic(tmp_path):
    d = Dicionario(caminho=tmp_path / "d.json")
    d.adicionar_termo("SINDEPRESTEM")
    return d


def test_erros_reais_do_whisper(tmp_path):
    texto = "Em nome da diretoria do Cinti Preste, quero agradecer. Fala o Cinder Prestem hoje."
    s = sugerir(texto, dic(tmp_path))
    assert [x.original for x in s] == ["Cinti Preste", "Cinder Prestem"]
    assert all(x.sugestao == "SINDEPRESTEM" for x in s)
    assert "SINDEPRESTEM, quero" in aplicar(texto, s)


def test_sem_falso_positivo(tmp_path):
    texto = "Eu faço negociação coletiva de trabalho aqui no sindicato há muitos anos, presente e presidente."
    assert sugerir(texto, dic(tmp_path)) == []


def test_termo_ja_correto_nao_vira_duvida(tmp_path):
    assert sugerir("O SINDEPRESTEM informa.", dic(tmp_path)) == []


def test_aprende_e_persiste_por_usuario(tmp_path):
    d = dic(tmp_path)
    d.aprender("Sindeprest", "SINDEPRESTEM")
    d.salvar()
    d2 = Dicionario.carregar(tmp_path / "d.json")
    s = sugerir("Moro perto do Sindeprest.", d2)
    assert len(s) == 1 and s[0].conhecida and s[0].sugestao == "SINDEPRESTEM"
