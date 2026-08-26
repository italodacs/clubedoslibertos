import pytest

from newsletter.notifier import avisar
from newsletter.publisher import criar_rascunho


class PosterFalso:
    """Substitui a chamada HTTP e guarda o que foi enviado."""

    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta or {"id": 4242}
        self.erro = erro
        self.chamadas = []

    def __call__(self, url, cabecalhos, corpo):
        self.chamadas.append({"url": url, "cabecalhos": cabecalhos, "corpo": corpo})
        if self.erro:
            raise self.erro
        return self.resposta


def test_cria_campanha_e_devolve_o_id():
    poster = PosterFalso()
    assert criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster) == 4242


def test_campanha_nasce_como_rascunho_e_nunca_agendada():
    """O publisher jamais dispara envio: quem envia e a pessoa que revisa."""
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert "scheduledAt" not in corpo


def test_envia_html_assunto_lista_e_remetente():
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert corpo["htmlContent"] == "<p>oi</p>"
    assert corpo["subject"] == "Assunto"
    assert corpo["recipients"] == {"listIds": [7]}
    assert corpo["sender"]["email"] == "clubedoslibertos@gmail.com"


def test_manda_a_chave_no_cabecalho_e_nao_no_corpo():
    poster = PosterFalso()
    criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)
    chamada = poster.chamadas[0]
    assert chamada["cabecalhos"]["api-key"] == "chave-x"
    assert "chave-x" not in str(chamada["corpo"])


def test_falha_do_brevo_propaga_para_quem_chamou():
    """Aqui a falha NAO e silenciada: o main precisa salvar o html e avisar."""
    poster = PosterFalso(erro=RuntimeError("500 do Brevo"))
    with pytest.raises(RuntimeError, match="500 do Brevo"):
        criar_rascunho("<p>oi</p>", "Assunto", 7, "chave-x", poster)


def test_aviso_vai_para_o_email_do_clube():
    poster = PosterFalso(resposta={"messageId": "abc"})
    avisar("Rascunho pronto", "3 itens nesta edicao.", "chave-x", poster)
    corpo = poster.chamadas[0]["corpo"]
    assert corpo["to"] == [{"email": "clubedoslibertos@gmail.com"}]
    assert corpo["subject"] == "Rascunho pronto"
    assert "3 itens nesta edicao." in corpo["htmlContent"]


def test_falha_do_aviso_nao_propaga():
    """Nao dar para avisar e ruim, mas nao pode derrubar uma execucao que deu certo."""
    poster = PosterFalso(erro=RuntimeError("sem rede"))
    avisar("Assunto", "Corpo", "chave-x", poster)  # nao levanta
