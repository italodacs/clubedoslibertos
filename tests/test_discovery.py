import datetime
import json

from newsletter.discovery import PROMPT, descobrir, ferramentas, interpretar

RESULTADOS = [
    {
        "titulo": "Programa Trainee Afirmativo 2027",
        "url": "https://alfa.com/trainee",
        "descricao": "Inscrições até 30/09/2026.",
        "categoria": "trainee",
        "afirmativa": True,
    },
    {
        "titulo": "Curso Gratuito de Excel",
        "url": "https://beta.com/excel",
        "descricao": "Online, com certificado.",
        "categoria": "educacao",
        "afirmativa": False,
    },
    {
        "titulo": "Blog: como se preparar",
        "url": "https://blog.com/dicas",
        "descricao": "Dicas de preparação.",
        "categoria": "trainee",
        "afirmativa": False,
    },
]


def _resposta(itens):
    return json.dumps({"itens": itens}, ensure_ascii=False)


MODELO_OK = _resposta(
    [
        {
            "url": "https://alfa.com/trainee",
            "titulo": "Programa Trainee Afirmativo 2027",
            "categoria": "trainee",
            "prazo": "2026-09-30",
            "afirmativa": True,
            "e_oportunidade": True,
        },
        {
            "url": "https://beta.com/excel",
            "titulo": "Curso Gratuito de Excel",
            "categoria": "educacao",
            "prazo": None,
            "afirmativa": False,
            "e_oportunidade": True,
        },
        {
            "url": "https://blog.com/dicas",
            "titulo": "Blog: como se preparar",
            "categoria": "trainee",
            "prazo": None,
            "afirmativa": False,
            "e_oportunidade": False,
        },
    ]
)


def test_interpreta_oportunidade_com_prazo_e_afirmativa():
    itens = interpretar(MODELO_OK, RESULTADOS)
    alfa = next(i for i in itens if i.url == "https://alfa.com/trainee")
    assert alfa.titulo == "Programa Trainee Afirmativo 2027"
    assert alfa.prazo == datetime.date(2026, 9, 30)
    assert alfa.afirmativa is True
    assert alfa.categoria == "trainee"
    assert alfa.fonte == "Busca na web"


def test_descarta_o_que_o_modelo_disse_nao_ser_oportunidade():
    """Artigo de blog aparece na busca; quem separa e o modelo."""
    itens = interpretar(MODELO_OK, RESULTADOS)
    assert not any(i.url == "https://blog.com/dicas" for i in itens)
    assert len(itens) == 2


def test_url_que_nao_veio_da_busca_e_descartada():
    """Defesa estrutural contra link inventado: a URL so pode ter vindo do Brave.

    Nao depende de o modelo se comportar — ainda que ele devolva uma URL
    plausivel que nunca existiu, ela nao passa daqui.
    """
    inventada = _resposta(
        [
            {
                "url": "https://empresa-que-nao-existe.com/trainee-2027",
                "titulo": "Trainee dos Sonhos",
                "categoria": "trainee",
                "prazo": None,
                "afirmativa": True,
                "e_oportunidade": True,
            }
        ]
    )
    assert interpretar(inventada, RESULTADOS) == []


def test_categoria_invalida_do_modelo_cai_para_a_da_consulta():
    """A consulta ja sabe o que estava procurando; palpite errado do modelo nao
    precisa custar o item."""
    resposta = _resposta(
        [
            {
                "url": "https://alfa.com/trainee",
                "titulo": "Programa Trainee",
                "categoria": "vaga_efetiva",
                "prazo": None,
                "afirmativa": False,
                "e_oportunidade": True,
            }
        ]
    )
    itens = interpretar(resposta, RESULTADOS)
    assert len(itens) == 1
    assert itens[0].categoria == "trainee"


def test_afirmativa_da_consulta_prevalece_quando_o_modelo_nega():
    """Se a consulta era explicitamente afirmativa, o resultado dela e
    afirmativo — o modelo nao tem como saber melhor que a consulta."""
    resposta = _resposta(
        [
            {
                "url": "https://alfa.com/trainee",
                "titulo": "Programa Trainee",
                "categoria": "trainee",
                "prazo": None,
                "afirmativa": False,
                "e_oportunidade": True,
            }
        ]
    )
    assert interpretar(resposta, RESULTADOS)[0].afirmativa is True


def test_prazo_ilegivel_vira_nulo_sem_descartar_o_item():
    resposta = _resposta(
        [
            {
                "url": "https://beta.com/excel",
                "titulo": "Curso",
                "categoria": "educacao",
                "prazo": "semana que vem",
                "afirmativa": False,
                "e_oportunidade": True,
            }
        ]
    )
    assert interpretar(resposta, RESULTADOS)[0].prazo is None


def test_resposta_com_cerca_de_markdown_e_aceita():
    texto = "```json\n" + MODELO_OK + "\n```"
    assert len(interpretar(texto, RESULTADOS)) == 2


def test_resposta_invalida_devolve_lista_vazia():
    assert interpretar("desculpe, nao encontrei nada", RESULTADOS) == []


def test_descobrir_devolve_itens_e_nenhum_erro():
    itens, erros = descobrir(RESULTADOS, lambda prompt: MODELO_OK)
    assert erros == []
    assert len(itens) == 2


def test_descobrir_sem_resultados_de_busca_nao_chama_o_modelo():
    """Sem nada para classificar, gastar cota do Gemini e desperdicio."""
    chamou = []

    def espiao(prompt):
        chamou.append(1)
        return MODELO_OK

    itens, erros = descobrir([], espiao)
    assert itens == []
    assert chamou == []


def test_descobrir_captura_falha_do_modelo():
    def explode(prompt):
        raise RuntimeError("cota esgotada")

    itens, erros = descobrir(RESULTADOS, explode)
    assert itens == []
    assert erros == ["cota esgotada"]


def test_prompt_deixa_claro_o_formato_e_a_regra_da_url():
    assert "URL" in PROMPT
    assert "JSON" in PROMPT


def test_classificacao_nao_leva_ferramenta_de_busca():
    """Quem busca agora e o Brave; o Gemini so le texto, nos dois usos."""
    assert ferramentas(com_busca=False) == []
