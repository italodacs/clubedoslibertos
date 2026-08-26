import datetime
import re

from newsletter import config
from newsletter.models import Oportunidade
from newsletter.renderer import renderizar


def _op(titulo, url, resumo="", afirmativa=False, prazo=None):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria="trainee",
        fonte="Portal Exemplo",
        prazo=prazo,
        afirmativa=afirmativa,
        resumo=resumo,
    )


BLOCOS = {
    "Trainees e estágios": [
        _op(
            "Trainee Alfa",
            "https://exemplo.org/a",
            resumo="Para quem esta comecando.",
            afirmativa=True,
            prazo=datetime.date(2026, 9, 30),
        )
    ],
    "Editais e formações": [],
}


def _html():
    return renderizar("Boa semana!", BLOCOS, "W36")


def test_inclui_abertura_titulo_e_link():
    html = _html()
    assert "Boa semana!" in html
    assert "Trainee Alfa" in html
    assert "https://exemplo.org/a" in html
    assert "Para quem esta comecando." in html


def test_usa_a_paleta_da_marca():
    html = _html()
    assert config.ROXO in html
    assert config.AMARELO in html


def test_inclui_cta_da_base_de_talentos_e_redes_sociais():
    html = _html()
    assert config.FORM_BASE_TALENTOS_URL in html
    assert config.INSTAGRAM_URL in html
    assert config.LINKEDIN_URL in html


def test_marca_oportunidade_afirmativa():
    assert "afirmativa" in _html().lower()


def test_mostra_prazo_quando_existe():
    assert "30/09/2026" in _html()


def test_bloco_vazio_nao_aparece_com_titulo_solto():
    assert "Editais e formações" not in _html()


def test_inclui_marcadores_dos_blocos_manuais():
    html = _html()
    assert "Vagas da semana" in html
    assert "Espaço do Clube" in html
    assert "preencha ou apague" in html.lower()


def test_toda_imagem_tem_texto_alternativo():
    for tag in re.findall(r"<img[^>]*>", _html()):
        assert "alt=" in tag, tag


def test_largura_fixa_de_600px_para_leitura_no_celular():
    assert "600px" in _html()


def test_nao_usa_folha_de_estilo_externa():
    """Cliente de email nao carrega CSS externo: tudo tem que ser inline."""
    html = _html()
    assert "<link" not in html
    assert "@import" not in html


def test_item_sem_prazo_diz_que_o_prazo_nao_foi_informado():
    """A spec pede o item marcado, nao a linha omitida: quem le precisa
    distinguir 'sem prazo' de 'prazo que a fonte nao publicou'."""
    blocos = {
        "Trainees e estágios": [_op("Trainee Sem Data", "https://exemplo.org/x")],
        "Editais e formações": [],
    }
    html = renderizar("Oi", blocos, "W36")
    assert "prazo não informado" in html


def test_item_com_prazo_nao_recebe_a_marca():
    assert "prazo não informado" not in _html()
