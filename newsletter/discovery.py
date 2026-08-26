"""Descoberta de oportunidades pelo Gemini com grounding de Google Search."""

import datetime
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import CATEGORIAS, Oportunidade

log = logging.getLogger(__name__)

MODELO = "gemini-2.5-flash"

PROMPT = """Você pesquisa oportunidades para o Clube dos Libertos, uma rede de
profissionais e estudantes negros no Brasil.

Busque na web oportunidades com INSCRIÇÕES ABERTAS HOJE nestas categorias:
- trainee: programas de trainee
- estagio: programas de estágio
- edital: editais, bolsas e chamadas públicas
- educacao: cursos e programas de formação gratuitos

Priorize oportunidades afirmativas para pessoas negras, e oportunidades
nacionais ou remotas.

Responda SOMENTE com um array JSON, sem texto em volta. Cada item:
{"titulo": str, "url": str, "categoria": str, "prazo": "AAAA-MM-DD" ou null,
 "afirmativa": bool}

A URL é obrigatória e precisa ser a página real da oportunidade, obtida na
busca. Se você não tem a URL de origem, NÃO inclua o item.
"""


def cliente_gemini(api_key: str) -> Callable[[str], str]:
    """Cria o chamador real do Gemini, com Google Search ligado."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=api_key)

    def chamar(prompt: str) -> str:
        resposta = cliente.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return resposta.text

    return chamar


def _sem_cerca(texto: str) -> str:
    """Remove a cerca de markdown que o modelo às vezes acrescenta."""
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def _data(valor) -> datetime.date | None:
    if not valor:
        return None
    try:
        return datetime.date.fromisoformat(str(valor))
    except ValueError:
        return None


def interpretar(texto: str) -> list[Oportunidade]:
    """Converte a resposta do modelo em oportunidades, descartando o inválido."""
    try:
        dados = json.loads(_sem_cerca(texto))
    except json.JSONDecodeError:
        log.warning("resposta do modelo nao e JSON valido")
        return []

    if not isinstance(dados, list):
        return []

    itens = []
    for bruto in dados:
        if not isinstance(bruto, dict):
            continue
        url = (bruto.get("url") or "").strip()
        categoria = bruto.get("categoria")
        if not url or categoria not in CATEGORIAS:
            continue
        itens.append(
            Oportunidade(
                titulo=(bruto.get("titulo") or "").strip(),
                url=url,
                categoria=categoria,
                fonte="Gemini",
                prazo=_data(bruto.get("prazo")),
                afirmativa=bool(bruto.get("afirmativa")),
            )
        )
    return itens


def descobrir(
    chamar_modelo: Callable[[str], str],
) -> tuple[list[Oportunidade], list[str]]:
    """Consulta o modelo. Falha não propaga — devolve lista vazia e o erro."""
    try:
        return interpretar(chamar_modelo(PROMPT)), []
    except Exception as erro:
        log.warning("discovery falhou: %s", erro)
        return [], [str(erro)]
