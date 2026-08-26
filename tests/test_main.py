import datetime
import json

import pytest

from newsletter.main import EdicaoVazia, executar, montar_assunto, semana_iso
from newsletter.models import Oportunidade

HOJE = datetime.date(2026, 8, 31)


def _op(titulo, url, categoria="trainee"):
    return Oportunidade(
        titulo=titulo,
        url=url,
        categoria=categoria,
        fonte="Exemplo",
        prazo=None,
        afirmativa=False,
    )


def _deps(tmp_path, **sobrescritas):
    avisos = []
    base = {
        "hoje": HOJE,
        "caminho_historico": tmp_path / "history.json",
        "coletar": lambda: ([_op("Trainee Alfa", "https://exemplo.org/a")], []),
        "descobrir": lambda: (
            [_op("Curso Beta", "https://exemplo.org/b", "educacao")],
            [],
        ),
        "verificar_link": lambda url: True,
        # Por padrao o enriquecimento e transparente: devolve o que recebeu.
        "enriquecer": lambda finalistas: (list(finalistas), []),
        "analisar": lambda itens: {
            "locais": [],
            "problemas": [],
            "parecer": "ok",
            "erro": None,
        },
        "escrever": lambda blocos: ("Boa semana!", blocos),
        "publicar": lambda html, assunto: 4242,
        "avisar": lambda assunto, corpo: avisos.append((assunto, corpo)),
        "salvar_html": lambda html: None,
    }
    base.update(sobrescritas)
    return base, avisos


def test_enriquecimento_pode_descartar_item_e_a_edicao_segue(tmp_path):
    """Item sem prazo cai no enriquecimento; a edicao sai com o que sobrou."""
    deps, _ = _deps(
        tmp_path,
        enriquecer=lambda fs: ([f for f in fs if f.categoria == "trainee"], []),
    )
    relatorio = executar(deps)
    assert relatorio["total"] == 1


def test_zero_apos_o_enriquecimento_aborta_sem_publicar(tmp_path):
    """Se nada tem prazo, nao existe edicao — e nao se cria rascunho vazio."""
    publicou = []
    deps, avisos = _deps(
        tmp_path,
        enriquecer=lambda fs: ([], []),
        publicar=lambda html, assunto: publicou.append(True),
    )
    with pytest.raises(EdicaoVazia):
        executar(deps)
    assert publicou == []
    assert len(avisos) == 1


def test_erro_do_enriquecimento_entra_no_relatorio(tmp_path):
    deps, _ = _deps(tmp_path, enriquecer=lambda fs: (list(fs), ["cota esgotada"]))
    relatorio = executar(deps)
    assert relatorio["erros_enriquecimento"] == ["cota esgotada"]


def test_historico_registra_o_titulo_enriquecido(tmp_path):
    """O titulo que vai para o historico e o publicado, com a empresa."""
    import dataclasses

    def com_empresa(fs):
        return [dataclasses.replace(f, titulo=f"Empresa — {f.titulo}") for f in fs], []

    deps, _ = _deps(tmp_path, enriquecer=com_empresa)
    executar(deps)
    dados = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert dados["itens"][0]["titulo"].startswith("Empresa — ")


def test_aviso_de_sucesso_carrega_o_relatorio_da_analise(tmp_path):
    """Quem revisa precisa saber onde olhar antes de clicar em enviar."""
    deps, avisos = _deps(
        tmp_path,
        analisar=lambda itens: {
            "locais": ["'Trainee 2024': titulo cita 2024, ano ja passou"],
            "problemas": ["'Curso X' parece publicidade"],
            "parecer": "Revisar dois itens",
            "erro": None,
        },
    )
    executar(deps)
    _, corpo = avisos[0]
    assert "2024" in corpo
    assert "publicidade" in corpo
    assert "Revisar dois itens" in corpo


def test_falha_da_analise_nao_impede_o_rascunho(tmp_path):
    """A analise e alerta, nao portao: se ela quebrar, a edicao ainda sai."""

    def explode(itens):
        raise RuntimeError("analise quebrou")

    deps, avisos = _deps(tmp_path, analisar=explode)
    relatorio = executar(deps)
    assert relatorio["campanha_id"] == 4242
    assert len(avisos) == 1


def test_semana_iso_usa_o_padrao_do_obsidian():
    assert semana_iso(datetime.date(2026, 8, 31)) == "W36"


def test_assunto_cita_a_semana_e_a_quantidade():
    blocos = {
        "Trainees e estágios": [_op("A", "https://a.org")],
        "Editais e formações": [],
    }
    assunto = montar_assunto(blocos, "W36")
    assert "W36" in assunto
    assert "1" in assunto


def test_execucao_feliz_publica_e_registra_historico(tmp_path):
    deps, avisos = _deps(tmp_path)
    relatorio = executar(deps)

    assert relatorio["campanha_id"] == 4242
    assert relatorio["total"] == 2
    dados = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(dados["itens"]) == 2
    assert len(avisos) == 1


def test_falha_das_fontes_fixas_segue_com_o_discovery(tmp_path):
    deps, _ = _deps(tmp_path, coletar=lambda: ([], ["Fonte Morta"]))
    relatorio = executar(deps)
    assert relatorio["total"] == 1
    assert relatorio["fontes_com_falha"] == ["Fonte Morta"]


def test_falha_do_gemini_segue_com_as_fontes_fixas(tmp_path):
    deps, _ = _deps(tmp_path, descobrir=lambda: ([], ["cota esgotada"]))
    relatorio = executar(deps)
    assert relatorio["total"] == 1
    assert relatorio["erros_discovery"] == ["cota esgotada"]


def test_zero_itens_aborta_sem_publicar(tmp_path):
    publicou = []
    deps, avisos = _deps(
        tmp_path,
        coletar=lambda: ([], []),
        descobrir=lambda: ([], []),
        publicar=lambda html, assunto: publicou.append(True),
    )
    with pytest.raises(EdicaoVazia):
        executar(deps)
    assert publicou == []
    assert len(avisos) == 1, "falha tambem precisa avisar"


def test_historico_nao_e_gravado_quando_a_publicacao_falha(tmp_path):
    """Gravar historico antes de publicar sumiria com a oportunidade na semana seguinte."""

    def explode(html, assunto):
        raise RuntimeError("500 do Brevo")

    deps, avisos = _deps(tmp_path, publicar=explode)
    with pytest.raises(RuntimeError):
        executar(deps)
    assert not (tmp_path / "history.json").exists()
    assert len(avisos) == 1


def test_html_e_salvo_quando_o_brevo_falha(tmp_path):
    salvos = []

    def explode(html, assunto):
        raise RuntimeError("500 do Brevo")

    deps, _ = _deps(
        tmp_path, publicar=explode, salvar_html=lambda html: salvos.append(html)
    )
    with pytest.raises(RuntimeError):
        executar(deps)
    assert len(salvos) == 1
    assert "Boa semana!" in salvos[0]


def test_item_ja_publicado_nao_volta(tmp_path):
    """Rodar duas vezes na mesma semana nao republica nada: tudo ja esta no historico,
    logo a segunda execucao aborta como edicao vazia."""
    deps, _ = _deps(tmp_path)
    executar(deps)
    with pytest.raises(EdicaoVazia):
        executar(deps)
