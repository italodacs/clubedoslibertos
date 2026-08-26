import datetime
import json

from newsletter.enrich import (
    MAX_CARACTERES,
    enriquecer,
    montar_titulo,
    trecho_da_pagina,
)
from newsletter.models import Oportunidade

HOJE = datetime.date(2026, 8, 26)


def _op(titulo, url, categoria="trainee"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Seja Trainee",
        prazo=None,
        afirmativa=False,
    )


PAGINA = """
<html><head><script>var x = 1;</script><style>.a{color:red}</style></head>
<body><nav>Menu Home Sobre</nav>
<h1>Programa de Trainee Itau 2027</h1>
<p>As inscricoes vao ate 30/09/2026. O programa e do Itau Unibanco.</p>
</body></html>
"""


def test_trecho_remove_script_e_style_e_limita_tamanho():
    t = trecho_da_pagina(PAGINA)
    assert "var x" not in t
    assert "color:red" not in t
    assert "Programa de Trainee Itau 2027" in t
    assert len(t) <= MAX_CARACTERES


def test_titulo_junta_empresa_quando_ela_nao_esta_no_titulo():
    assert montar_titulo("Programa de Estagio 2027", "Ultragaz") == (
        "Ultragaz — Programa de Estagio 2027"
    )


def test_titulo_nao_repete_empresa_que_ja_aparece():
    titulo = "Trainee Itau 2027 abre inscricoes"
    assert montar_titulo(titulo, "Itau") == titulo


def test_titulo_sem_empresa_fica_como_esta():
    assert montar_titulo("Gestao financeira", "") == "Gestao financeira"


def _resposta(itens):
    return json.dumps({"itens": itens}, ensure_ascii=False)


def test_enriquece_com_empresa_e_prazo():
    op = _op("Programa de Estagio 2027", "https://a.org/1")
    resposta = _resposta(
        [
            {
                "url": "https://a.org/1",
                "empresa": "Ultragaz",
                "prazo": "2026-09-30",
                "e_oportunidade": True,
            }
        ]
    )
    itens, erros = enriquecer([op], {"https://a.org/1": PAGINA}, lambda p: resposta, HOJE)
    assert erros == []
    assert len(itens) == 1
    assert itens[0].prazo == datetime.date(2026, 9, 30)
    assert itens[0].titulo == "Ultragaz — Programa de Estagio 2027"


def test_descarta_item_sem_prazo_encontrado():
    """A Presidencia decidiu que prazo e obrigatorio: sem data, nao publica."""
    op = _op("Vaga sem data", "https://a.org/1")
    resposta = _resposta(
        [{"url": "https://a.org/1", "empresa": "X", "prazo": None, "e_oportunidade": True}]
    )
    itens, _ = enriquecer([op], {"https://a.org/1": PAGINA}, lambda p: resposta, HOJE)
    assert itens == []


def test_descarta_prazo_vencido_mesmo_que_a_pagina_publique():
    """Pagina de 2025 ainda no ar: a data manda, nao a existencia da pagina."""
    op = _op("Trainee 2025", "https://a.org/1")
    resposta = _resposta(
        [
            {
                "url": "https://a.org/1",
                "empresa": "X",
                "prazo": "2025-11-30",
                "e_oportunidade": True,
            }
        ]
    )
    itens, _ = enriquecer([op], {"https://a.org/1": PAGINA}, lambda p: resposta, HOJE)
    assert itens == []


def test_descarta_o_que_nao_e_oportunidade():
    """Video e artigo aparecem nas fontes; aqui eles caem."""
    op = _op("Video | O que e o SAT?", "https://a.org/1")
    resposta = _resposta(
        [
            {
                "url": "https://a.org/1",
                "empresa": "",
                "prazo": "2026-12-01",
                "e_oportunidade": False,
            }
        ]
    )
    itens, _ = enriquecer([op], {"https://a.org/1": PAGINA}, lambda p: resposta, HOJE)
    assert itens == []


def test_item_sem_pagina_baixada_nao_e_enviado_ao_modelo():
    """Pagina que nao respondeu nao vale gastar token para classificar."""
    op = _op("Sem pagina", "https://a.org/1")
    itens, erros = enriquecer([op], {}, lambda p: _resposta([]), HOJE)
    assert itens == []


def test_url_inventada_pelo_modelo_e_ignorada():
    op = _op("Vaga", "https://a.org/1")
    resposta = _resposta(
        [
            {
                "url": "https://inventada.com/x",
                "empresa": "Y",
                "prazo": "2026-12-01",
                "e_oportunidade": True,
            }
        ]
    )
    itens, _ = enriquecer([op], {"https://a.org/1": PAGINA}, lambda p: resposta, HOJE)
    assert itens == []


def test_falha_do_modelo_devolve_lista_vazia_e_o_erro():
    op = _op("Vaga", "https://a.org/1")

    def explode(prompt):
        raise RuntimeError("cota esgotada")

    itens, erros = enriquecer([op], {"https://a.org/1": PAGINA}, explode, HOJE)
    assert itens == []
    assert erros == ["cota esgotada"]


def test_sem_itens_nao_chama_o_modelo():
    chamou = []

    def espiao(prompt):
        chamou.append(1)
        return _resposta([])

    itens, erros = enriquecer([], {}, espiao, HOJE)
    assert itens == []
    assert chamou == []
