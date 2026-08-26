"""Classificação dos resultados de busca em oportunidades.

Divisão de trabalho deliberada: o Brave (em `newsletter.search`) devolve as
URLs, e o Gemini **apenas classifica** o que a busca achou — separa oportunidade
de artigo, extrai prazo, confirma categoria. O modelo nunca produz URL.

Isso vale mais que uma instrução no prompt: `interpretar` descarta qualquer URL
que não esteja entre os resultados da busca, então link inventado deixa de
depender de o modelo se comportar.
"""

import datetime
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import CATEGORIAS, Oportunidade

log = logging.getLogger(__name__)

# Conta nova do AI Studio não tem acesso a modelo descontinuado: em 26/08/2026
# o `gemini-2.5-flash` respondeu 404 apontando para este.
MODELO = "gemini-3.6-flash"

PROMPT = """Você separa oportunidades reais de conteúdo editorial, para a
newsletter do Clube dos Libertos — uma rede de profissionais e estudantes negros
no Brasil.

Abaixo estão resultados de busca. Para cada um, decida se é uma **oportunidade
com inscrição aberta** (programa de trainee, programa de estágio, edital, bolsa,
curso gratuito) ou se é apenas conteúdo sobre o assunto (artigo, vídeo, ranking,
publicidade de curso preparatório, página institucional).

Resultados:
{resultados}

Responda SOMENTE com JSON, sem texto em volta:
{{"itens": [{{"url": str, "titulo": str, "categoria": str,
  "prazo": "AAAA-MM-DD" ou null, "afirmativa": bool, "e_oportunidade": bool}}]}}

Regras:
- Repita a URL exatamente como veio. Não crie, corrija nem complete URL.
- `titulo`: limpe o título para leitura, sem inventar informação.
- `categoria`: trainee, estagio, edital ou educacao.
- `prazo`: só se a data estiver no texto do resultado.
- `e_oportunidade`: false para artigo, vídeo, ranking ou publicidade.
"""


def ferramentas(com_busca: bool) -> list:
    """Quais ferramentas a chamada leva.

    Hoje nenhuma das duas usa busca: quem busca é o Brave. A opção continua
    aqui porque no free tier o grounding de Google Search não tem cota, e ligar
    a ferramenta à toa fazia a chamada morrer com 429 mesmo sem precisar dela.
    """
    if not com_busca:
        return []
    from google.genai import types

    return [types.Tool(google_search=types.GoogleSearch())]


def cliente_gemini(api_key: str, com_busca: bool = False) -> Callable[[str], str]:
    """Cria o chamador real do Gemini."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=api_key)
    tools = ferramentas(com_busca)

    def chamar(prompt: str) -> str:
        resposta = cliente.models.generate_content(
            model=MODELO,
            contents=prompt,
            config=types.GenerateContentConfig(tools=tools),
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


def _descrever(resultados: list[dict]) -> str:
    return "\n".join(
        f"- {r['url']}\n  titulo: {r['titulo']}\n  resumo: {r['descricao']}"
        for r in resultados
    )


def interpretar(texto: str, resultados: list[dict]) -> list[Oportunidade]:
    """Converte a resposta do modelo em oportunidades.

    Só passa item cuja URL veio dos `resultados` da busca. Categoria e flag
    afirmativa da consulta prevalecem sobre o palpite do modelo: a consulta já
    sabia o que estava procurando.
    """
    try:
        dados = json.loads(_sem_cerca(texto))
    except json.JSONDecodeError:
        log.warning("resposta do modelo nao e JSON valido")
        return []

    por_url = {r["url"]: r for r in resultados}
    itens = []

    for bruto in dados.get("itens") or []:
        if not isinstance(bruto, dict):
            continue
        url = (bruto.get("url") or "").strip()
        origem = por_url.get(url)
        if origem is None:
            if url:
                log.warning("descartando url que nao veio da busca: %s", url)
            continue
        if not bruto.get("e_oportunidade"):
            continue

        categoria = bruto.get("categoria")
        if categoria not in CATEGORIAS:
            categoria = origem["categoria"]

        titulo = (bruto.get("titulo") or "").strip() or origem["titulo"]
        if not titulo:
            continue

        itens.append(
            Oportunidade(
                titulo=titulo,
                url=url,
                categoria=categoria,
                fonte="Busca na web",
                prazo=_data(bruto.get("prazo")),
                afirmativa=bool(origem["afirmativa"] or bruto.get("afirmativa")),
            )
        )

    return itens


def descobrir(
    resultados: list[dict],
    chamar_modelo: Callable[[str], str],
) -> tuple[list[Oportunidade], list[str]]:
    """Classifica os resultados da busca. Falha não propaga."""
    if not resultados:
        return [], []
    try:
        texto = chamar_modelo(PROMPT.format(resultados=_descrever(resultados)))
        return interpretar(texto, resultados), []
    except Exception as erro:
        log.warning("discovery falhou: %s", erro)
        return [], [str(erro)]
