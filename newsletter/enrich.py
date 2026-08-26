"""Enriquecimento: abre a página de cada finalista para extrair empresa e prazo.

A listagem quase nunca traz a data limite — ela está dentro da página da vaga.
Sem abrir a página, a edição sairia inteira com "prazo não informado", e a
Presidência decidiu em 26/08/2026 que prazo é obrigatório.

Esta etapa também é a peneira que as fontes fixas não tinham: item de fonte fixa
antes ia direto para a edição, o que deixava passar vídeo, artigo e página de
programa encerrado que continua no ar.

Três regras duras, todas testadas:
- item sem prazo encontrado não publica;
- prazo vencido não publica, mesmo com a página viva;
- URL que o modelo devolver e que não estava na lista é ignorada.
"""

import dataclasses
import datetime
import json
import logging
import re
from collections.abc import Callable

from bs4 import BeautifulSoup

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

# Quanto de cada página vai no prompt. O suficiente para pegar cabeçalho, texto
# de abertura e a linha de prazo, sem estourar o contexto com dez páginas.
MAX_CARACTERES = 2500

PROMPT = """Você prepara a newsletter do Clube dos Libertos. Abaixo estão
páginas de oportunidades. Para cada uma, extraia:

- `empresa`: a organização que oferece a oportunidade. String vazia se não
  estiver claro.
- `prazo`: a data limite de inscrição, em AAAA-MM-DD. **null se a página não
  disser.** Não estime, não deduza a partir do ano no título.
- `e_oportunidade`: false se for artigo, vídeo, ranking, página institucional,
  publicidade de curso preparatório, ou programa cujas inscrições já
  encerraram.

Hoje é {hoje}.

Páginas:
{paginas}

Responda SOMENTE com JSON, sem texto em volta:
{{"itens": [{{"url": str, "empresa": str, "prazo": "AAAA-MM-DD" ou null,
  "e_oportunidade": bool}}]}}

Repita a URL exatamente como veio.
"""


def trecho_da_pagina(html: str) -> str:
    """Texto legível da página, sem script nem style, cortado no limite."""
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = re.sub(r"\s+", " ", sopa.get_text(" ", strip=True))
    return texto[:MAX_CARACTERES]


def montar_titulo(titulo: str, empresa: str) -> str:
    """Põe a empresa na frente, salvo quando ela já aparece no título."""
    empresa = (empresa or "").strip()
    if not empresa:
        return titulo
    if empresa.lower() in titulo.lower():
        return titulo
    return f"{empresa} — {titulo}"


def _sem_cerca(texto: str) -> str:
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def _data(valor) -> datetime.date | None:
    if not valor:
        return None
    try:
        return datetime.date.fromisoformat(str(valor))
    except ValueError:
        return None


def enriquecer(
    oportunidades: list[Oportunidade],
    paginas: dict[str, str],
    chamar_modelo: Callable[[str], str],
    hoje: datetime.date,
) -> tuple[list[Oportunidade], list[str]]:
    """Devolve só os itens com prazo válido, já com a empresa no título."""
    com_pagina = [op for op in oportunidades if paginas.get(op.url)]
    if not com_pagina:
        return [], []

    descricao = "\n\n".join(
        f"URL: {op.url}\nTítulo na listagem: {op.titulo}\n"
        f"Texto: {trecho_da_pagina(paginas[op.url])}"
        for op in com_pagina
    )

    try:
        texto = chamar_modelo(PROMPT.format(hoje=hoje.isoformat(), paginas=descricao))
        dados = json.loads(_sem_cerca(texto))
    except Exception as erro:
        log.warning("enriquecimento falhou: %s", erro)
        return [], [str(erro)]

    por_url = {op.url: op for op in com_pagina}
    resultado: list[Oportunidade] = []

    for bruto in dados.get("itens") or []:
        if not isinstance(bruto, dict):
            continue
        op = por_url.get((bruto.get("url") or "").strip())
        if op is None:
            continue
        if not bruto.get("e_oportunidade"):
            log.info("descartado, nao e oportunidade: %s", op.titulo[:60])
            continue

        prazo = _data(bruto.get("prazo"))
        if prazo is None:
            log.info("descartado, prazo nao encontrado: %s", op.titulo[:60])
            continue
        if prazo < hoje:
            log.info("descartado, prazo vencido em %s: %s", prazo, op.titulo[:60])
            continue

        resultado.append(
            dataclasses.replace(
                op,
                titulo=montar_titulo(op.titulo, bruto.get("empresa", "")),
                prazo=prazo,
            )
        )

    return resultado, []
