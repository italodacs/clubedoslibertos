import json

from newsletter.models import Oportunidade
from newsletter.writer import ABERTURA_PADRAO, escrever


def _op(titulo, url):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


BLOCOS = {
    "Trainees e estágios": [_op("Trainee Alfa", "https://exemplo.org/a")],
    "Editais e formações": [_op("Curso Beta", "https://exemplo.org/b")],
}


def _modelo_ok(prompt):
    return json.dumps(
        {
            "abertura": "Boa semana, Libertos!",
            "resumos": {
                "https://exemplo.org/a": "Programa para quem esta comecando.",
                "https://exemplo.org/b": "Curso gratuito e online.",
            },
        },
        ensure_ascii=False,
    )


def test_preenche_abertura_e_resumos():
    abertura, blocos = escrever(BLOCOS, _modelo_ok)
    assert abertura == "Boa semana, Libertos!"
    assert blocos["Trainees e estágios"][0].resumo == "Programa para quem esta comecando."
    assert blocos["Editais e formações"][0].resumo == "Curso gratuito e online."


def test_nao_altera_titulo_nem_url():
    _, blocos = escrever(BLOCOS, _modelo_ok)
    item = blocos["Trainees e estágios"][0]
    assert item.titulo == "Trainee Alfa"
    assert item.url == "https://exemplo.org/a"


def test_falha_do_modelo_usa_abertura_padrao_e_mantem_os_itens():
    def explode(prompt):
        raise RuntimeError("cota esgotada")

    abertura, blocos = escrever(BLOCOS, explode)
    assert abertura == ABERTURA_PADRAO
    assert blocos["Trainees e estágios"][0].titulo == "Trainee Alfa"
    assert blocos["Trainees e estágios"][0].resumo == ""


def test_resumo_ausente_para_um_item_nao_quebra_os_outros():
    def parcial(prompt):
        return json.dumps(
            {"abertura": "Oi", "resumos": {"https://exemplo.org/a": "Tem resumo."}}
        )

    _, blocos = escrever(BLOCOS, parcial)
    assert blocos["Trainees e estágios"][0].resumo == "Tem resumo."
    assert blocos["Editais e formações"][0].resumo == ""


def test_prompt_recebe_os_titulos_dos_itens_curados():
    recebidos = []

    def espiao(prompt):
        recebidos.append(prompt)
        return _modelo_ok(prompt)

    escrever(BLOCOS, espiao)
    assert "Trainee Alfa" in recebidos[0]
    assert "Curso Beta" in recebidos[0]
