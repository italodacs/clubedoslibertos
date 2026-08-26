from newsletter.search import CONSULTAS, pesquisar

RESPOSTA_BRAVE = {
    "web": {
        "results": [
            {
                "title": "Programa de Trainee 2027 — Empresa Alfa",
                "url": "https://alfa.com/trainee",
                "description": "Inscrições abertas até 30/09/2026.",
            },
            {
                "title": "Blog: como se preparar para trainee",
                "url": "https://blog.com/dicas",
                "description": "Dicas de preparação.",
            },
        ]
    }
}


def test_consultas_cobrem_as_quatro_categorias():
    categorias = {c["categoria"] for c in CONSULTAS}
    assert categorias == {"trainee", "estagio", "edital", "educacao"}


def test_existe_consulta_afirmativa():
    """Oportunidade afirmativa nao tem fonte fixa nenhuma: se a busca nao
    procurar por ela de proposito, ela simplesmente nao aparece."""
    assert any(c.get("afirmativa") for c in CONSULTAS)


def test_pesquisa_devolve_titulo_url_e_descricao():
    resultados, erros = pesquisar(
        [{"consulta": "trainee 2027", "categoria": "trainee", "afirmativa": False}],
        lambda consulta: RESPOSTA_BRAVE,
    )
    assert erros == []
    assert len(resultados) == 2
    primeiro = resultados[0]
    assert primeiro["titulo"] == "Programa de Trainee 2027 — Empresa Alfa"
    assert primeiro["url"] == "https://alfa.com/trainee"
    assert primeiro["descricao"] == "Inscrições abertas até 30/09/2026."
    assert primeiro["categoria"] == "trainee"


def test_marca_afirmativa_conforme_a_consulta():
    resultados, _ = pesquisar(
        [{"consulta": "vaga afirmativa", "categoria": "trainee", "afirmativa": True}],
        lambda consulta: RESPOSTA_BRAVE,
    )
    assert all(r["afirmativa"] for r in resultados)


def test_consulta_que_falha_nao_derruba_as_outras():
    def instavel(consulta):
        if "quebra" in consulta:
            raise RuntimeError("500 do Brave")
        return RESPOSTA_BRAVE

    resultados, erros = pesquisar(
        [
            {"consulta": "quebra aqui", "categoria": "trainee", "afirmativa": False},
            {"consulta": "ok", "categoria": "estagio", "afirmativa": False},
        ],
        instavel,
    )
    assert len(erros) == 1
    assert len(resultados) == 2


def test_resposta_sem_resultados_nao_quebra():
    resultados, erros = pesquisar(
        [{"consulta": "nada", "categoria": "trainee", "afirmativa": False}],
        lambda consulta: {},
    )
    assert resultados == []
    assert erros == []


def test_deduplica_url_repetida_entre_consultas():
    """A mesma vaga aparece em mais de uma consulta; nao vale mandar duas vezes
    para o modelo classificar."""
    consultas = [
        {"consulta": "a", "categoria": "trainee", "afirmativa": False},
        {"consulta": "b", "categoria": "trainee", "afirmativa": False},
    ]
    resultados, _ = pesquisar(consultas, lambda c: RESPOSTA_BRAVE)
    assert len(resultados) == 2
