import datetime
from pathlib import Path

from newsletter.collector import coletar

FIXTURES = Path(__file__).parent / "fixtures"

FONTE_RSS = {
    "nome": "Feed de Exemplo",
    "url": "https://exemplo.org/feed.xml",
    "tipo": "rss",
    "categoria": "trainee",
    "afirmativa": False,
}

FONTE_HTML = {
    "nome": "Portal de Cursos",
    "url": "https://exemplo.org/cursos",
    "tipo": "html",
    "categoria": "educacao",
    "seletor": ".card-curso",
    "afirmativa": False,
}


def _feed():
    return (FIXTURES / "feed_exemplo.xml").read_text(encoding="utf-8")


def _pagina():
    return (FIXTURES / "pagina_exemplo.html").read_text(encoding="utf-8")


def _buscador(mapa):
    def buscar(url):
        if url not in mapa:
            raise RuntimeError(f"fonte fora do ar: {url}")
        return mapa[url]

    return buscar


def test_coleta_itens_de_rss():
    itens, falhas = coletar([FONTE_RSS], _buscador({FONTE_RSS["url"]: _feed()}))
    assert falhas == []
    assert len(itens) == 2
    assert itens[0].titulo == "Programa de Trainee 2027"
    assert itens[0].url == "https://exemplo.org/trainee-2027"
    assert itens[0].categoria == "trainee"
    assert itens[0].fonte == "Feed de Exemplo"


def test_extrai_prazo_em_formato_brasileiro():
    itens, _ = coletar([FONTE_RSS], _buscador({FONTE_RSS["url"]: _feed()}))
    assert itens[0].prazo == datetime.date(2026, 9, 30)
    assert itens[1].prazo is None


def test_coleta_itens_de_html_com_seletor():
    itens, falhas = coletar([FONTE_HTML], _buscador({FONTE_HTML["url"]: _pagina()}))
    assert falhas == []
    assert [i.titulo for i in itens] == [
        "Curso Gratuito de Dados",
        "Curso Gratuito de Gestão",
    ]


def test_resolve_link_relativo_contra_a_url_da_fonte():
    itens, _ = coletar([FONTE_HTML], _buscador({FONTE_HTML["url"]: _pagina()}))
    assert itens[0].url == "https://exemplo.org/curso/dados"


def test_marca_afirmativa_conforme_a_fonte():
    fonte = {**FONTE_RSS, "afirmativa": True}
    itens, _ = coletar([fonte], _buscador({fonte["url"]: _feed()}))
    assert all(i.afirmativa for i in itens)


def test_fonte_que_falha_nao_derruba_as_outras():
    fonte_morta = {**FONTE_RSS, "nome": "Fonte Morta", "url": "https://morta.org/feed.xml"}
    itens, falhas = coletar(
        [fonte_morta, FONTE_RSS], _buscador({FONTE_RSS["url"]: _feed()})
    )
    assert falhas == ["Fonte Morta"]
    assert len(itens) == 2


def test_titulo_de_link_com_marcacao_interna_nao_vem_grudado():
    """Ancora com <mark>/<span> dentro: sem separador, 'Trainee' + 'Tributario'
    virava 'TraineeTributario'."""
    fonte = {**FONTE_HTML, "seletor": ".card-vaga"}
    itens, _ = coletar([fonte], _buscador({fonte["url"]: _pagina()}))
    assert itens[0].titulo == "Trainee Tributário"


def test_titulo_pode_vir_do_bloco_em_vez_do_link():
    """Portal cujo link diz so 'Estagiario': o bloco tem a empresa e distingue
    um item do outro, evitando que a dedup por titulo colapse tudo em um."""
    fonte = {**FONTE_HTML, "seletor": ".card-vaga", "titulo": "bloco"}
    itens, _ = coletar([fonte], _buscador({fonte["url"]: _pagina()}))
    assert itens[0].titulo == "Trainee Tributário Empresa Alfa"
    assert itens[1].titulo == "Trainee Tributário Empresa Beta"


def test_descarta_href_que_nao_e_http():
    """javascript:, mailto: e afins nao sao oportunidade."""
    fonte = {**FONTE_HTML, "seletor": ".card-ruim"}
    itens, _ = coletar([fonte], _buscador({fonte["url"]: _pagina()}))
    assert itens == []


def test_item_sem_link_e_descartado():
    rss_sem_link = """<?xml version="1.0"?><rss version="2.0"><channel>
        <item><title>Sem link</title></item>
        </channel></rss>"""
    itens, _ = coletar([FONTE_RSS], _buscador({FONTE_RSS["url"]: rss_sem_link}))
    assert itens == []
