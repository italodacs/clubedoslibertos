"""Curadoria: decide o que entra na edição. Código puro, sem rede.

A única dependência externa é a verificação de link, que entra por injeção
para que os testes rodem offline.
"""

import datetime
import re
import unicodedata
from collections.abc import Callable, Iterable

from newsletter.config import AREAS_MEMBROS, ESTADOS_MEMBROS, LIMITE_POR_BLOCO
from newsletter.history import chave
from newsletter.models import Oportunidade, bloco_de

PONTOS_AFIRMATIVA = 100
PONTOS_AREA = 10
PONTOS_ESTADO = 5


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação, para comparar títulos."""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9 ]", " ", sem_acento).strip()


def deduplicar(
    oportunidades: Iterable[Oportunidade], historico: set[str]
) -> list[Oportunidade]:
    """Remove o que já foi publicado e o que repete dentro da própria semana."""
    resultado: list[Oportunidade] = []
    chaves_vistas: set[str] = set()
    titulos_vistos: set[str] = set()

    for op in oportunidades:
        k = chave(op.url)
        titulo = _normalizar(op.titulo)
        if k in historico or k in chaves_vistas or titulo in titulos_vistos:
            continue
        chaves_vistas.add(k)
        titulos_vistos.add(titulo)
        resultado.append(op)

    return resultado


def remover_vencidas(
    oportunidades: Iterable[Oportunidade], hoje: datetime.date
) -> list[Oportunidade]:
    """Descarta inscrição encerrada. Item sem prazo identificado é mantido."""
    return [op for op in oportunidades if op.prazo is None or op.prazo >= hoje]


def pontuar(op: Oportunidade) -> int:
    """Relevância: afirmativa primeiro, depois aderência a área e estado."""
    pontos = 0
    if op.afirmativa:
        pontos += PONTOS_AFIRMATIVA

    texto = _normalizar(f"{op.titulo} {op.resumo}")
    if any(_normalizar(area) in texto for area in AREAS_MEMBROS):
        pontos += PONTOS_AREA

    titulo_cru = op.titulo.upper()
    if any(re.search(rf"\b{estado}\b", titulo_cru) for estado in ESTADOS_MEMBROS):
        pontos += PONTOS_ESTADO

    return pontos


def curar(
    oportunidades: Iterable[Oportunidade],
    historico: set[str],
    hoje: datetime.date,
    verificar_link: Callable[[str], bool],
) -> dict[str, list[Oportunidade]]:
    """Pipeline de curadoria completo, agrupando por bloco da edição.

    A ordem importa: dedupe e prazo são baratos e vêm antes da verificação de
    link, que gasta rede. Não se checa link de item que já foi descartado.
    """
    itens = deduplicar(oportunidades, historico)
    itens = remover_vencidas(itens, hoje)
    itens = [op for op in itens if verificar_link(op.url)]

    blocos: dict[str, list[Oportunidade]] = {
        "Trainees e estágios": [],
        "Editais e formações": [],
    }
    for op in itens:
        blocos[bloco_de(op.categoria)].append(op)

    for nome, lista in blocos.items():
        lista.sort(key=pontuar, reverse=True)
        blocos[nome] = lista[:LIMITE_POR_BLOCO]

    return blocos
