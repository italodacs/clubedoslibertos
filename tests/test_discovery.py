import datetime
from pathlib import Path

from newsletter.discovery import PROMPT, descobrir, interpretar

FIXTURES = Path(__file__).parent / "fixtures"
RESPOSTA = (FIXTURES / "resposta_gemini.json").read_text(encoding="utf-8")


def test_interpreta_item_valido():
    itens = interpretar(RESPOSTA)
    primeiro = next(i for i in itens if i.categoria == "trainee")
    assert primeiro.titulo == "Programa Trainee Afirmativo 2027"
    assert primeiro.url == "https://exemplo.org/trainee-afirmativo"
    assert primeiro.prazo == datetime.date(2026, 9, 30)
    assert primeiro.afirmativa is True
    assert primeiro.fonte == "Gemini"


def test_descarta_item_sem_url():
    """Item sem URL rastreavel e a principal defesa contra oportunidade inventada."""
    itens = interpretar(RESPOSTA)
    assert all(item.url for item in itens)
    assert not any(i.titulo == "Oportunidade sem link" for i in itens)


def test_descarta_categoria_desconhecida():
    assert not any(i.titulo == "Categoria que nao existe" for i in interpretar(RESPOSTA))


def test_prazo_ilegivel_vira_nulo_sem_descartar_o_item():
    item = next(i for i in interpretar(RESPOSTA) if i.titulo == "Prazo ilegivel")
    assert item.prazo is None


def test_resposta_com_cerca_de_markdown_e_aceita():
    texto = (
        '```json\n[{"titulo":"A","url":"https://a.org","categoria":"trainee",'
        '"prazo":null,"afirmativa":false}]\n```'
    )
    assert len(interpretar(texto)) == 1


def test_resposta_invalida_devolve_lista_vazia():
    assert interpretar("desculpe, nao encontrei nada") == []


def test_descobrir_devolve_itens_e_nenhum_erro():
    itens, erros = descobrir(lambda prompt: RESPOSTA)
    assert erros == []
    assert len(itens) == 3


def test_descobrir_captura_falha_do_modelo():
    def explode(prompt):
        raise RuntimeError("cota esgotada")

    itens, erros = descobrir(explode)
    assert itens == []
    assert erros == ["cota esgotada"]


def test_prompt_pede_url_de_origem_e_json():
    assert "URL" in PROMPT
    assert "JSON" in PROMPT


def test_writer_nao_leva_a_ferramenta_de_busca():
    """No free tier o grounding nao tem cota. Levar a ferramenta numa chamada
    que so redige fazia o writer morrer no mesmo 429 do discovery."""
    from newsletter.discovery import ferramentas

    assert ferramentas(com_busca=False) == []


def test_discovery_leva_a_ferramenta_de_busca():
    from newsletter.discovery import ferramentas

    assert len(ferramentas(com_busca=True)) == 1
