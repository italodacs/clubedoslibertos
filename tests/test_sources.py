from pathlib import Path

import yaml

from newsletter.collector import carregar_fontes
from newsletter.models import CATEGORIAS

SOURCES = Path(__file__).parent.parent / "newsletter" / "sources.yml"

CAMPOS_OBRIGATORIOS = {"nome", "url", "tipo", "categoria", "afirmativa"}

# Categorias que ainda não têm fonte fixa aprovada e são cobertas apenas pelo
# discovery. Ver docs/fontes-avaliadas.md para o que foi testado e reprovado.
SEM_FONTE_FIXA = set()


def _fontes():
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))


def test_arquivo_existe_e_tem_pelo_menos_quatro_fontes():
    fontes = _fontes()
    assert isinstance(fontes, list)
    assert len(fontes) >= 4


def test_toda_fonte_tem_os_campos_obrigatorios():
    for fonte in _fontes():
        faltando = CAMPOS_OBRIGATORIOS - set(fonte)
        assert not faltando, f"{fonte.get('nome')} sem os campos {faltando}"


def test_tipo_e_categoria_sao_validos():
    for fonte in _fontes():
        assert fonte["tipo"] in ("rss", "html"), fonte["nome"]
        assert fonte["categoria"] in CATEGORIAS, fonte["nome"]


def test_fonte_html_declara_seletor():
    for fonte in _fontes():
        if fonte["tipo"] == "html":
            assert fonte.get("seletor"), f"{fonte['nome']} e html e nao tem seletor"


def test_titulo_declarado_e_bloco_ou_um_seletor_util():
    """'bloco' ou um seletor CSS. String vazia seria um engano silencioso."""
    for fonte in _fontes():
        if "titulo" in fonte:
            assert fonte["titulo"], fonte["nome"]


def test_url_e_absoluta_e_https():
    for fonte in _fontes():
        assert fonte["url"].startswith("https://"), fonte["nome"]


def test_nome_de_fonte_nao_repete():
    nomes = [fonte["nome"] for fonte in _fontes()]
    assert len(nomes) == len(set(nomes))


def test_categoria_sem_fonte_fixa_esta_declarada_como_tal():
    """Categoria sem fonte fixa e uma decisao registrada, nao um esquecimento.

    Ela continua em CATEGORIAS de proposito: o discovery devolve itens dessa
    categoria e `interpretar` descartaria tudo que nao estivesse na tupla.
    """
    cobertas = {fonte["categoria"] for fonte in _fontes()}
    descobertas = set(CATEGORIAS) - cobertas
    assert descobertas == SEM_FONTE_FIXA, (
        f"categorias sem fonte fixa mudaram: {descobertas}. "
        "Atualize SEM_FONTE_FIXA e docs/fontes-avaliadas.md."
    )


def test_carregar_fontes_le_o_arquivo_padrao():
    fontes = carregar_fontes()
    assert len(fontes) == len(_fontes())
