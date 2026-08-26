"""Orquestração do pipeline semanal.

Toda dependência externa entra pelo dicionário `dependencias`, o que deixa o
fluxo inteiro testável sem rede.
"""

import datetime
import logging
import os
import sys
from pathlib import Path

import requests

from newsletter import (
    collector,
    curator,
    discovery,
    enrich,
    history,
    notifier,
    publisher,
    qa,
    renderer,
    search,
    writer,
)

log = logging.getLogger(__name__)

RAIZ = Path(__file__).parent.parent
CAMINHO_HISTORICO = RAIZ / "history.json"
CAMINHO_SAIDA = RAIZ / "saida" / "edicao.html"


FOLGA_DE_CANDIDATOS = 3


class EdicaoVazia(Exception):
    """Nenhum item sobrou após a curadoria — não se cria rascunho vazio."""


def semana_iso(hoje: datetime.date) -> str:
    return f"W{hoje.isocalendar().week:02d}"


def montar_assunto(blocos: dict, semana: str) -> str:
    total = sum(len(itens) for itens in blocos.values())
    return f"Oportunidades da semana {semana} — {total} para você conferir"


def _verificar_link(url: str) -> bool:
    """Link vivo responde. HEAD primeiro; alguns servidores só aceitam GET."""
    try:
        resposta = requests.head(url, timeout=15, allow_redirects=True)
        if resposta.status_code >= 400:
            resposta = requests.get(url, timeout=15, allow_redirects=True)
        return resposta.status_code < 400
    except Exception:
        return False


def _descobrir(buscar_web, chamar_texto) -> tuple[list, list[str]]:
    """Busca no Serper e manda o Gemini classificar o que voltou."""
    resultados, erros_busca = search.pesquisar(search.CONSULTAS, buscar_web)
    log.info("busca na web devolveu %d resultados", len(resultados))
    itens, erros_modelo = discovery.descobrir(resultados, chamar_texto)
    return itens, [*erros_busca, *erros_modelo]


def _baixar_paginas(oportunidades) -> dict[str, str]:
    """Busca a página de cada finalista. Página que não responde fica de fora,
    e o item cai por falta de prazo — melhor do que publicar data inventada."""
    paginas = {}
    for op in oportunidades:
        try:
            paginas[op.url] = collector.buscar_http(op.url, timeout=20)
        except Exception as erro:
            log.info("nao baixei %s: %s", op.url, erro)
    log.info("baixei %d de %d paginas", len(paginas), len(oportunidades))
    return paginas


def executar(dependencias: dict) -> dict:
    """Roda o pipeline. Devolve o relatório da execução."""
    hoje = dependencias["hoje"]
    caminho_historico = dependencias["caminho_historico"]
    avisar = dependencias["avisar"]
    semana = semana_iso(hoje)

    fixas, fontes_com_falha = dependencias["coletar"]()
    achadas, erros_discovery = dependencias["descobrir"]()
    log.info("coletadas %d das fontes fixas, %d do discovery", len(fixas), len(achadas))

    # Folga de 3: o enriquecimento exige prazo e descarta boa parte, então
    # cortar na cota antes dele deixaria a edição curta.
    candidatos = curator.curar(
        [*fixas, *achadas],
        history.carregar(caminho_historico),
        hoje,
        dependencias["verificar_link"],
        folga=FOLGA_DE_CANDIDATOS,
    )
    finalistas = [op for lista in candidatos.values() for op in lista]
    log.info("%d candidatos para enriquecer", len(finalistas))

    enriquecidos, erros_enriquecimento = dependencias["enriquecer"](finalistas)
    log.info("%d sobreviveram ao enriquecimento", len(enriquecidos))

    blocos = curator.agrupar_e_cortar(enriquecidos)
    total = sum(len(itens) for itens in blocos.values())

    relatorio = {
        "semana": semana,
        "total": total,
        "candidatos": len(finalistas),
        "por_bloco": {bloco: len(itens) for bloco, itens in blocos.items()},
        "fontes_com_falha": fontes_com_falha,
        "erros_discovery": erros_discovery,
        "erros_enriquecimento": erros_enriquecimento,
    }

    if total == 0:
        relatorio["abortou"] = True
        avisar(
            f"[Newsletter {semana}] nenhuma oportunidade nova",
            f"Nada sobrou apos a curadoria.\n\n{relatorio}",
        )
        raise EdicaoVazia(f"semana {semana} sem itens")

    abertura, blocos = dependencias["escrever"](blocos)
    html = renderer.renderizar(abertura, blocos, semana)
    assunto = montar_assunto(blocos, semana)

    try:
        campanha_id = dependencias["publicar"](html, assunto)
    except Exception as erro:
        dependencias["salvar_html"](html)
        avisar(
            f"[Newsletter {semana}] falha ao criar o rascunho",
            f"O HTML foi salvo para nao perder a edicao.\nErro: {erro}\n\n{relatorio}",
        )
        raise

    # O histórico só é gravado depois de publicar: gravar antes sumiria com a
    # oportunidade na semana seguinte se a publicação falhasse.
    history.registrar(
        caminho_historico,
        [op for itens in blocos.values() for op in itens],
        hoje,
    )

    relatorio["campanha_id"] = campanha_id
    relatorio["url_campanha"] = publisher.URL_CAMPANHA.format(id=campanha_id)

    # A análise é alerta, não portão: roda depois de o rascunho já existir, e
    # falhar nela não pode custar a edição.
    publicados = [op for itens in blocos.values() for op in itens]
    try:
        analise = qa.formatar_relatorio(dependencias["analisar"](publicados), total)
    except Exception as erro:
        log.warning("analise falhou: %s", erro)
        analise = f"(a analise nao rodou: {erro})"

    avisar(
        f"[Newsletter {semana}] rascunho pronto para revisao",
        f"{relatorio['url_campanha']}\n\n{analise}\n\n{relatorio}",
    )
    return relatorio


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    gemini_key = os.environ["GEMINI_API_KEY"]
    serper_key = os.environ["SERPER_KEY"]
    brevo_key = os.environ["BREVO_API_KEY"]
    lista_id = int(os.environ["BREVO_LIST_ID"])

    # Nenhuma das duas chamadas leva ferramenta de busca: quem busca e o Serper.
    # O Gemini classifica o que a busca achou e redige a edicao.
    chamar_texto = discovery.cliente_gemini(gemini_key, com_busca=False)
    buscar_web = search.cliente_serper(serper_key)

    def salvar_html(html: str) -> None:
        CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
        CAMINHO_SAIDA.write_text(html, encoding="utf-8")
        log.info("html salvo em %s", CAMINHO_SAIDA)

    dependencias = {
        "hoje": datetime.date.today(),
        "caminho_historico": CAMINHO_HISTORICO,
        "coletar": lambda: collector.coletar(
            collector.carregar_fontes(), collector.buscar_http
        ),
        "descobrir": lambda: _descobrir(buscar_web, chamar_texto),
        "verificar_link": _verificar_link,
        "enriquecer": lambda finalistas: enrich.enriquecer(
            finalistas,
            _baixar_paginas(finalistas),
            chamar_texto,
            datetime.date.today(),
        ),
        "escrever": lambda blocos: writer.escrever(blocos, chamar_texto),
        "publicar": lambda html, assunto: publisher.criar_rascunho(
            html, assunto, lista_id, brevo_key
        ),
        "analisar": lambda itens: qa.analisar(
            itens, datetime.date.today(), chamar_texto
        ),
        "avisar": lambda assunto, corpo: notifier.avisar(assunto, corpo, brevo_key),
        "salvar_html": salvar_html,
    }

    try:
        executar(dependencias)
    except EdicaoVazia:
        log.warning("edicao vazia — nenhum rascunho criado")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
