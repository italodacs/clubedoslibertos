"""Curadoria: decide o que entra na edição. Código puro, sem rede.

A única dependência externa é a verificação de link, que entra por injeção
para que os testes rodem offline.
"""

import datetime
import logging
import re
import unicodedata
from collections.abc import Callable, Iterable

from newsletter.config import AREAS_MEMBROS, ESTADOS_MEMBROS, LIMITES_POR_CATEGORIA
from newsletter.history import chave
from newsletter.models import Oportunidade, bloco_de

log = logging.getLogger(__name__)

PONTOS_AFIRMATIVA = 100
PONTOS_AREA = 10
PONTOS_ESTADO = 5

# Teto de checagens de link por categoria. Sem ele, uma categoria em que tudo
# está morto viraria uma requisição por candidato — dezenas de chamadas para
# publicar zero item.
MAX_VERIFICACOES_POR_CATEGORIA = max(LIMITES_POR_CATEGORIA.values()) * 3


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


def agrupar_e_cortar(
    oportunidades: Iterable[Oportunidade],
) -> dict[str, list[Oportunidade]]:
    """Agrupa nos blocos da edição e aplica a cota de cada categoria.

    Etapa final, depois do enriquecimento: só aqui se sabe quais itens
    sobreviveram à exigência de prazo.
    """
    blocos: dict[str, list[Oportunidade]] = {
        "Trainees e estágios": [],
        "Editais e formações": [],
    }
    restante = dict(LIMITES_POR_CATEGORIA)

    for op in sorted(oportunidades, key=pontuar, reverse=True):
        if restante.get(op.categoria, 0) <= 0:
            continue
        restante[op.categoria] -= 1
        blocos[bloco_de(op.categoria)].append(op)

    return blocos


def curar(
    oportunidades: Iterable[Oportunidade],
    historico: set[str],
    hoje: datetime.date,
    verificar_link: Callable[[str], bool],
    folga: int = 1,
) -> dict[str, list[Oportunidade]]:
    """Pipeline de curadoria completo, agrupando por bloco da edição.

    A cota é por categoria, e não por bloco: "Trainees e estágios" reúne duas
    categorias, e sem cota separada um dia farto de trainees ocuparia as vagas
    de estágio.

    A ordem importa, e é toda ela sobre não gastar rede à toa: os filtros
    baratos (dedupe, prazo) vêm primeiro, depois o ranking, e só então a
    verificação de link — que desce a lista ordenada e para assim que a cota
    está cheia. Verificar antes de cortar significaria checar 140 links para
    publicar 10, e bater nas fontes 140 vezes por semana sem necessidade.
    """
    itens = deduplicar(oportunidades, historico)
    itens = remover_vencidas(itens, hoje)

    candidatos: dict[str, list[Oportunidade]] = {}
    for op in itens:
        candidatos.setdefault(op.categoria, []).append(op)

    blocos: dict[str, list[Oportunidade]] = {
        "Trainees e estágios": [],
        "Editais e formações": [],
    }
    for categoria, lista in candidatos.items():
        lista.sort(key=pontuar, reverse=True)
        escolhidos = _com_link_vivo(
            lista, verificar_link, LIMITES_POR_CATEGORIA[categoria] * folga
        )
        blocos[bloco_de(categoria)].extend(escolhidos)

    # Categorias diferentes chegam ao mesmo bloco em ordens separadas; a
    # reordenação final garante que a afirmativa continue no topo do bloco.
    for nome in blocos:
        blocos[nome].sort(key=pontuar, reverse=True)

    return blocos


def _com_link_vivo(
    ordenados: list[Oportunidade],
    verificar_link: Callable[[str], bool],
    limite: int,
) -> list[Oportunidade]:
    """Desce a lista já ordenada até completar a cota da categoria.

    Link morto no topo não deixa a edição curta: entra o próximo colocado. Mas
    a busca desiste depois de `MAX_VERIFICACOES_POR_CATEGORIA` tentativas, para
    que uma categoria inteira de links quebrados não vire uma enxurrada de
    requisições.
    """
    escolhidos: list[Oportunidade] = []
    for tentativa, op in enumerate(ordenados, start=1):
        if tentativa > max(MAX_VERIFICACOES_POR_CATEGORIA, limite * 2):
            log.warning(
                "desisti apos %d verificacoes de link; %d item(ns) na categoria",
                MAX_VERIFICACOES_POR_CATEGORIA,
                len(escolhidos),
            )
            break
        if verificar_link(op.url):
            escolhidos.append(op)
            if len(escolhidos) == limite:
                break
    return escolhidos
