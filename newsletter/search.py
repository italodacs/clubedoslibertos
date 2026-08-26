"""Busca na web pela API do Serper (google.serper.dev).

O Gemini free tier não tem cota para o grounding de Google Search, então quem
descobre oportunidade fora das fontes fixas é o Serper. A divisão de trabalho é
deliberada: **o Serper devolve as URLs, o Gemini apenas classifica o que o
Serper achou**. Assim link inventado deixa de ser uma questão de o modelo se
comportar e passa a ser estruturalmente impossível — a URL só pode ter vindo da
busca.
"""

import logging
from collections.abc import Callable

import requests

log = logging.getLogger(__name__)

API = "https://google.serper.dev/search"
TIMEOUT = 25
RESULTADOS_POR_CONSULTA = 10

# Uma consulta por frente de conteúdo. A consulta afirmativa existe porque
# nenhuma das fontes fixas cobre esse terreno: se a busca não procurar por ela
# de propósito, oportunidade afirmativa simplesmente não aparece na edição.
CONSULTAS = (
    {
        "consulta": "programa de trainee 2027 inscrições abertas Brasil",
        "categoria": "trainee",
        "afirmativa": False,
    },
    {
        "consulta": "programa de trainee afirmativo pessoas negras inscrições abertas",
        "categoria": "trainee",
        "afirmativa": True,
    },
    {
        "consulta": "programa de estágio 2027 inscrições abertas Brasil",
        "categoria": "estagio",
        "afirmativa": False,
    },
    {
        "consulta": "programa de estágio afirmativo pessoas negras inscrições abertas",
        "categoria": "estagio",
        "afirmativa": True,
    },
    {
        "consulta": "edital bolsa de estudos intercâmbio inscrições abertas 2026",
        "categoria": "edital",
        "afirmativa": False,
    },
    {
        "consulta": "bolsa de estudos para pessoas negras inscrições abertas",
        "categoria": "edital",
        "afirmativa": True,
    },
    {
        "consulta": "curso online gratuito com certificado inscrições abertas",
        "categoria": "educacao",
        "afirmativa": False,
    },
)


def cliente_serper(api_key: str) -> Callable[[str], dict]:
    """Cria o buscador real. Uma chamada por consulta."""

    def buscar(consulta: str) -> dict:
        resposta = requests.post(
            API,
            json={
                "q": consulta,
                "num": RESULTADOS_POR_CONSULTA,
                "gl": "br",
                "hl": "pt-br",
            },
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        resposta.raise_for_status()
        return resposta.json()

    return buscar


def pesquisar(
    consultas, buscar: Callable[[str], dict]
) -> tuple[list[dict], list[str]]:
    """Roda as consultas e devolve os resultados achatados, mais os erros.

    Consulta que falha não derruba as outras: um 429 pontual não pode custar a
    edição inteira.
    """
    encontrados: list[dict] = []
    erros: list[str] = []
    vistos: set[str] = set()

    for item in consultas:
        try:
            dados = buscar(item["consulta"])
        except Exception as erro:
            log.warning("consulta %r falhou: %s", item["consulta"], erro)
            erros.append(f"{item['consulta']}: {erro}")
            continue

        for r in dados.get("organic") or []:
            url = (r.get("link") or "").strip()
            if not url or url in vistos:
                continue
            vistos.add(url)
            encontrados.append(
                {
                    "titulo": (r.get("title") or "").strip(),
                    "url": url,
                    "descricao": (r.get("snippet") or "").strip(),
                    "categoria": item["categoria"],
                    "afirmativa": bool(item.get("afirmativa")),
                }
            )

    return encontrados, erros
