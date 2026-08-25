import datetime

import pytest

from newsletter.models import CATEGORIAS, Oportunidade, bloco_de


def test_trainee_e_estagio_vao_para_o_mesmo_bloco():
    assert bloco_de("trainee") == "Trainees e estágios"
    assert bloco_de("estagio") == "Trainees e estágios"


def test_edital_e_educacao_vao_para_o_mesmo_bloco():
    assert bloco_de("edital") == "Editais e formações"
    assert bloco_de("educacao") == "Editais e formações"


def test_categoria_desconhecida_levanta_erro():
    with pytest.raises(ValueError, match="categoria desconhecida"):
        bloco_de("vaga_efetiva")


def test_todas_as_categorias_tem_bloco():
    for categoria in CATEGORIAS:
        assert bloco_de(categoria)


def test_oportunidade_e_imutavel_e_tem_resumo_vazio_por_padrao():
    op = Oportunidade(
        titulo="Programa de Trainee 2027",
        url="https://exemplo.org/trainee",
        categoria="trainee",
        fonte="Exemplo",
        prazo=datetime.date(2026, 9, 30),
        afirmativa=True,
    )
    assert op.resumo == ""
    with pytest.raises(Exception):
        op.titulo = "outro"
