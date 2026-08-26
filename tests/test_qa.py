import datetime
import json

from newsletter.models import Oportunidade
from newsletter.qa import analisar, formatar_relatorio, verificacoes_locais

HOJE = datetime.date(2026, 8, 26)


def _op(titulo, url="https://a.org/1", prazo=None, categoria="trainee"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Seja Trainee",
        prazo=prazo,
        afirmativa=False,
        resumo="Resumo qualquer.",
    )


# --- verificacoes que nao precisam de IA ---


def test_acusa_ano_passado_no_titulo():
    itens = [_op("Trainee 2025 da Empresa", prazo=datetime.date(2026, 12, 1))]
    achados = verificacoes_locais(itens, HOJE)
    assert any("2025" in a for a in achados)


def test_nao_acusa_ano_futuro_no_titulo():
    itens = [_op("Trainee 2027 da Empresa", prazo=datetime.date(2026, 12, 1))]
    assert verificacoes_locais(itens, HOJE) == []


def test_acusa_prazo_vencido():
    itens = [_op("Trainee da Empresa", prazo=datetime.date(2026, 8, 25))]
    achados = verificacoes_locais(itens, HOJE)
    assert any("vencido" in a.lower() for a in achados)


def test_acusa_item_sem_prazo():
    achados = verificacoes_locais([_op("Trainee da Empresa", prazo=None)], HOJE)
    assert any("sem prazo" in a.lower() for a in achados)


def test_acusa_titulo_curto_demais():
    """'Gestao financeira' nao diz de quem e a oportunidade."""
    itens = [_op("Gestao", prazo=datetime.date(2026, 12, 1))]
    achados = verificacoes_locais(itens, HOJE)
    assert any("gen" in a.lower() for a in achados)


def test_acusa_url_repetida_entre_itens():
    p = datetime.date(2026, 12, 1)
    itens = [
        _op("Trainee A da Empresa", url="https://a.org/x", prazo=p),
        _op("Trainee B da Empresa", url="https://a.org/x", prazo=p),
    ]
    achados = verificacoes_locais(itens, HOJE)
    assert any("repetid" in a.lower() for a in achados)


def test_edicao_saudavel_nao_gera_achado():
    p = datetime.date(2026, 12, 1)
    itens = [
        _op("Itau — Programa de Trainee 2027", url="https://a.org/1", prazo=p),
        _op("Ultragaz — Programa de Estagio 2027", url="https://a.org/2", prazo=p),
    ]
    assert verificacoes_locais(itens, HOJE) == []


# --- parecer do modelo ---


def test_analisar_junta_achados_locais_e_parecer_do_modelo():
    itens = [_op("Trainee 2024 velho", prazo=datetime.date(2026, 12, 1))]
    resposta = json.dumps(
        {"problemas": ["O terceiro item parece publicidade"], "parecer": "Aceitavel"}
    )
    r = analisar(itens, HOJE, lambda p: resposta)
    assert any("2024" in a for a in r["locais"])
    assert r["problemas"] == ["O terceiro item parece publicidade"]
    assert r["parecer"] == "Aceitavel"


def test_falha_do_modelo_nao_perde_as_verificacoes_locais():
    """A analise e um alerta, nao um portao: se a IA cair, o que da para
    checar sem ela continua valendo."""

    def explode(prompt):
        raise RuntimeError("cota esgotada")

    itens = [_op("Trainee 2024 velho", prazo=datetime.date(2026, 12, 1))]
    r = analisar(itens, HOJE, explode)
    assert any("2024" in a for a in r["locais"])
    assert r["erro"] == "cota esgotada"


def test_relatorio_menciona_quantidade_e_achados():
    r = {
        "locais": ["item 1: ano 2024 no titulo"],
        "problemas": ["item 3 parece publicidade"],
        "parecer": "Revisar antes de enviar",
        "erro": None,
    }
    texto = formatar_relatorio(r, total=7)
    assert "7" in texto
    assert "2024" in texto
    assert "publicidade" in texto
    assert "Revisar antes de enviar" in texto


def test_relatorio_de_edicao_limpa_diz_que_nada_foi_achado():
    r = {"locais": [], "problemas": [], "parecer": "Tudo certo", "erro": None}
    texto = formatar_relatorio(r, total=5)
    assert "nenhum" in texto.lower()
