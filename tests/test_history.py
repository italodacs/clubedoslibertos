import datetime
import json

from newsletter.history import carregar, chave, registrar
from newsletter.models import Oportunidade


def _op(url, titulo="Titulo"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


def test_chave_ignora_maiusculas_e_barra_final():
    assert chave("https://Exemplo.org/Vaga/") == chave("https://exemplo.org/Vaga")


def test_chave_ignora_parametros_de_rastreamento():
    limpa = chave("https://exemplo.org/vaga")
    assert chave("https://exemplo.org/vaga?utm_source=news&utm_medium=email") == limpa
    assert chave("https://exemplo.org/vaga?fbclid=abc") == limpa


def test_chave_preserva_parametro_significativo():
    assert chave("https://exemplo.org/vaga?id=42") != chave("https://exemplo.org/vaga")


def test_carregar_arquivo_inexistente_devolve_conjunto_vazio(tmp_path):
    assert carregar(tmp_path / "nao_existe.json") == set()


def test_registrar_e_carregar_faz_ida_e_volta(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(caminho, [_op("https://exemplo.org/a")], datetime.date(2026, 8, 31))
    assert chave("https://exemplo.org/a") in carregar(caminho)


def test_registrar_preserva_o_que_ja_existia(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(caminho, [_op("https://exemplo.org/a")], datetime.date(2026, 8, 31))
    registrar(caminho, [_op("https://exemplo.org/b")], datetime.date(2026, 9, 7))
    chaves = carregar(caminho)
    assert chave("https://exemplo.org/a") in chaves
    assert chave("https://exemplo.org/b") in chaves


def test_arquivo_guarda_titulo_e_data_para_auditoria(tmp_path):
    caminho = tmp_path / "history.json"
    registrar(
        caminho,
        [_op("https://exemplo.org/a", titulo="Trainee Alfa")],
        datetime.date(2026, 8, 31),
    )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    registro = dados["itens"][0]
    assert registro["titulo"] == "Trainee Alfa"
    assert registro["data_edicao"] == "2026-08-31"
