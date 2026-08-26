"""Coleta determinística das fontes fixas cadastradas em sources.yml."""

import datetime
import logging
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

TIMEOUT = 20
USER_AGENT = (
    "ClubeDosLibertos-Newsletter/1.0 "
    "(+https://github.com/italodacs/clubedoslibertos)"
)

_DATA_BR = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def buscar_http(url: str) -> str:
    """Busca o conteúdo de uma URL. Levanta exceção em qualquer erro."""
    resposta = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
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
    fontes: list[dict], buscar: Callable[[str], str]
) -> tuple[list[Oportunidade], list[str]]:
    """Percorre as fontes fixas. Fonte que falha é registrada, não propagada."""
    encontrados: list[Oportunidade] = []
    falhas: list[str] = []

    for fonte in fontes:
        try:
            conteudo = buscar(fonte["url"])
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
