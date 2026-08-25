import datetime

from newsletter.curator import curar, deduplicar, pontuar, remover_vencidas
from newsletter.history import chave
from newsletter.models import Oportunidade

HOJE = datetime.date(2026, 8, 31)


def _op(url, titulo="Titulo", categoria="trainee", prazo=None, afirmativa=False):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Exemplo",
        prazo=prazo,
        afirmativa=afirmativa,
    )


def _aceita_tudo(url):
    return True


# --- deduplicacao ---


def test_remove_item_ja_publicado_no_historico():
    op = _op("https://exemplo.org/a")
    assert deduplicar([op], {chave("https://exemplo.org/a")}) == []


def test_remove_duplicata_dentro_da_propria_semana():
    a = _op("https://exemplo.org/a?utm_source=x")
    b = _op("https://exemplo.org/a")
    assert len(deduplicar([a, b], set())) == 1


def test_remove_titulo_praticamente_igual_com_url_diferente():
    a = _op("https://exemplo.org/a", titulo="Programa de Trainee 2027")
    b = _op("https://outro.org/b", titulo="programa de trainee 2027")
    assert len(deduplicar([a, b], set())) == 1


def test_mantem_titulos_diferentes():
    a = _op("https://exemplo.org/a", titulo="Trainee Alfa")
    b = _op("https://outro.org/b", titulo="Estagio Beta")
    assert len(deduplicar([a, b], set())) == 2


# --- prazo ---


def test_remove_inscricao_encerrada():
    vencida = _op("https://exemplo.org/a", prazo=datetime.date(2026, 8, 30))
    assert remover_vencidas([vencida], HOJE) == []


def test_mantem_prazo_de_hoje():
    hoje = _op("https://exemplo.org/a", prazo=HOJE)
    assert remover_vencidas([hoje], HOJE) == [hoje]


def test_mantem_item_sem_prazo_identificado():
    sem_prazo = _op("https://exemplo.org/a", prazo=None)
    assert remover_vencidas([sem_prazo], HOJE) == [sem_prazo]


# --- ranking ---


def test_afirmativa_pontua_mais_que_nao_afirmativa():
    afirmativa = _op("https://exemplo.org/a", afirmativa=True)
    comum = _op("https://exemplo.org/b", afirmativa=False)
    assert pontuar(afirmativa) > pontuar(comum)


def test_area_de_membro_pontua_mais_que_area_de_fora():
    dentro = _op("https://exemplo.org/a", titulo="Estagio em Servico Social")
    fora = _op("https://exemplo.org/b", titulo="Estagio em Medicina Veterinaria")
    assert pontuar(dentro) > pontuar(fora)


def test_estado_de_membro_pontua_mais_que_estado_de_fora():
    dentro = _op("https://exemplo.org/a", titulo="Trainee em Fortaleza - CE")
    fora = _op("https://exemplo.org/b", titulo="Trainee em Curitiba - PR")
    assert pontuar(dentro) > pontuar(fora)


def test_afirmativa_vence_aderencia_de_area():
    afirmativa_fora = _op(
        "https://exemplo.org/a", titulo="Trainee em Medicina Veterinaria", afirmativa=True
    )
    comum_dentro = _op("https://exemplo.org/b", titulo="Trainee em Administracao")
    assert pontuar(afirmativa_fora) > pontuar(comum_dentro)


# --- curar (integracao dos passos) ---


def test_curar_agrupa_por_bloco():
    itens = [
        _op("https://exemplo.org/a", categoria="trainee"),
        _op("https://exemplo.org/b", categoria="educacao", titulo="Curso Gratuito"),
    ]
    blocos = curar(itens, set(), HOJE, _aceita_tudo)
    assert list(blocos["Trainees e estágios"]) == [itens[0]]
    assert list(blocos["Editais e formações"]) == [itens[1]]


def test_curar_descarta_link_morto():
    itens = [_op("https://exemplo.org/morto")]
    blocos = curar(itens, set(), HOJE, lambda url: False)
    assert blocos["Trainees e estágios"] == []


def test_curar_corta_em_cinco_itens_por_bloco():
    itens = [
        _op(f"https://exemplo.org/{i}", titulo=f"Trainee {i}") for i in range(9)
    ]
    blocos = curar(itens, set(), HOJE, _aceita_tudo)
    assert len(blocos["Trainees e estágios"]) == 5


def test_curar_ordena_afirmativa_primeiro():
    comum = _op("https://exemplo.org/a", titulo="Trainee Comum")
    afirmativa = _op("https://exemplo.org/b", titulo="Trainee Afirmativo", afirmativa=True)
    blocos = curar([comum, afirmativa], set(), HOJE, _aceita_tudo)
    assert blocos["Trainees e estágios"][0] == afirmativa


def test_curar_verifica_link_apenas_do_que_sobrou():
    """Link morto e caro de checar: nao gastar rede em item que ja foi descartado."""
    visitados = []

    def registrando(url):
        visitados.append(url)
        return True

    itens = [
        _op("https://exemplo.org/vencida", prazo=datetime.date(2026, 1, 1)),
        _op("https://exemplo.org/viva", titulo="Outra"),
    ]
    curar(itens, set(), HOJE, registrando)
    assert visitados == ["https://exemplo.org/viva"]
