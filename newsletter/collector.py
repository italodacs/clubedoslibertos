"""Coleta determinística das fontes fixas cadastradas em sources.yml."""

import datetime
import logging
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

TIMEOUT_PADRAO = 20
USER_AGENT = (
    "ClubeDosLibertos-Newsletter/1.0 "
    "(+https://github.com/italodacs/clubedoslibertos)"
)

_DATA_BR = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")

# Sufixos de dois níveis: em "loja.sebrae.com.br" o domínio registrável são os
# três últimos rótulos, não os dois.
_SUFIXOS_COMPOSTOS = ("com.br", "org.br", "gov.br", "net.br", "edu.br", "co.uk")


def dominio_base(url: str) -> str:
    """Domínio registrável da URL, para comparar fonte e destino.

    `loja.sebrae.com.br` e `sebrae.com.br` são a mesma casa;
    `estagio.alupar.com.br` e `ciadeestagios.com.br` não são.
    """
    host = urlsplit(url).netloc.lower().split(":")[0]
    partes = host.split(".")
    n = 3 if host.endswith(_SUFIXOS_COMPOSTOS) else 2
    return ".".join(partes[-n:]) if len(partes) >= n else host


def buscar_http(url: str, timeout: int = TIMEOUT_PADRAO) -> str:
    """Busca o conteúdo de uma URL. Levanta exceção em qualquer erro."""
    resposta = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resposta.raise_for_status()
    return resposta.text


def _extrair_prazo(texto: str) -> datetime.date | None:
    """Procura uma data dd/mm/aaaa no texto. Ausência não é erro."""
    achado = _DATA_BR.search(texto or "")
    if not achado:
        return None
    dia, mes, ano = (int(g) for g in achado.groups())
    try:
        return datetime.date(ano, mes, dia)
    except ValueError:
        return None


def _do_rss(conteudo: str, fonte: dict) -> list[Oportunidade]:
    feed = feedparser.parse(conteudo)
    itens = []
    for entrada in feed.entries:
        url = entrada.get("link")
        if not url:
            continue
        itens.append(
            Oportunidade(
                titulo=entrada.get("title", "").strip(),
                url=url,
                categoria=fonte["categoria"],
                fonte=fonte["nome"],
                prazo=_extrair_prazo(entrada.get("description", "")),
                afirmativa=bool(fonte.get("afirmativa", False)),
            )
        )
    return itens


def _texto(elemento) -> str:
    """Texto legível de um elemento, com espaço entre as tags internas.

    Sem o separador, uma âncora como `<mark>Trainee</mark><span>Tributário</span>`
    sai como "TraineeTributário".
    """
    return re.sub(r"\s+", " ", elemento.get_text(" ", strip=True)).strip()


def _titulo_de(bloco, ancora, modo: str | None) -> str:
    """De onde sai o título do item.

    Sem `modo`, o texto do próprio link — serve para a maioria das fontes.
    `"bloco"` usa o texto do bloco inteiro, para portal cujo link diz apenas
    "Estagiário" e a empresa está em volta. Qualquer outro valor é um seletor
    CSS dentro do bloco, para card cuja âncora é vazia e o título mora num
    elemento à parte.
    """
    if modo == "bloco":
        return _texto(bloco)
    if modo:
        alvo = bloco.select_one(modo)
        return _texto(alvo) if alvo else ""
    return _texto(ancora)


def _do_html(conteudo: str, fonte: dict) -> list[Oportunidade]:
    sopa = BeautifulSoup(conteudo, "html.parser")
    modo_titulo = fonte.get("titulo")
    itens = []
    for bloco in sopa.select(fonte["seletor"]):
        # O seletor pode casar com um bloco em volta do link ou com o próprio
        # link — este último é o único caminho estável em site cujas classes
        # são hashes gerados, onde só resta selecionar pelo href.
        if bloco.name == "a" and bloco.get("href"):
            ancora = bloco
        else:
            ancora = bloco.find("a", href=True)
        if not ancora:
            continue
        url = urljoin(fonte["url"], ancora["href"])
        # javascript:, mailto: e afins não são oportunidade.
        if not url.startswith(("http://", "https://")):
            continue
        # A fonte da informação é o link: item que sai do domínio da fonte não é
        # página dela. Vaga do Cia de Estágios apontando para
        # estagio.alupar.com.br fica de fora.
        if dominio_base(url) != dominio_base(fonte["url"]):
            log.info("fora do dominio de %s: %s", fonte["nome"], url)
            continue
        titulo = _titulo_de(bloco, ancora, modo_titulo)
        # Título vazio viraria uma linha em branco no email.
        if not titulo:
            continue
        itens.append(
            Oportunidade(
                titulo=titulo,
                url=url,
                categoria=fonte["categoria"],
                fonte=fonte["nome"],
                prazo=_extrair_prazo(bloco.get_text(" ", strip=True)),
                afirmativa=bool(fonte.get("afirmativa", False)),
            )
        )
    return itens


def coletar(
    fontes: list[dict], buscar: Callable[[str, int], str]
) -> tuple[list[Oportunidade], list[str]]:
    """Percorre as fontes fixas. Fonte que falha é registrada, não propagada.

    Cada fonte pode declarar o próprio `timeout`: portal lento não é portal
    fora do ar, e o padrão de 20s derrubava uma fonte que só é vagarosa a
    partir da região do runner.
    """
    encontrados: list[Oportunidade] = []
    falhas: list[str] = []

    for fonte in fontes:
        try:
            conteudo = buscar(fonte["url"], fonte.get("timeout", TIMEOUT_PADRAO))
            if fonte["tipo"] == "rss":
                encontrados.extend(_do_rss(conteudo, fonte))
            else:
                encontrados.extend(_do_html(conteudo, fonte))
        except Exception as erro:
            log.warning("fonte %s falhou: %s", fonte["nome"], erro)
            falhas.append(fonte["nome"])

    return encontrados, falhas


def carregar_fontes(caminho: str | Path | None = None) -> list[dict]:
    """Lê sources.yml. Sem argumento, usa o arquivo ao lado deste módulo."""
    arquivo = Path(caminho) if caminho else Path(__file__).parent / "sources.yml"
    return yaml.safe_load(arquivo.read_text(encoding="utf-8"))
