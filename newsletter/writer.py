"""Redação da edição: abertura e resumo de cada item.

A IA redige, não decide o que entra — recebe apenas itens já curados.
"""

import dataclasses
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

ABERTURA_PADRAO = (
    "Boa semana, Libertos! Seguem as oportunidades que encontramos para vocês."
)

_MODELO_PROMPT = """Você escreve a newsletter semanal do Clube dos Libertos, uma
rede de profissionais e estudantes negros no Brasil. O tom é acolhedor, direto e
sem jargão corporativo.

Escreva:
1. Uma abertura de no máximo 2 frases, sobre o conjunto das oportunidades desta semana.
2. Um resumo de 2 a 3 linhas para cada oportunidade, dizendo para quem serve e o
   que a pessoa ganha. Não repita o título e não invente informação que não está aqui.

Oportunidades desta semana:
{itens}

Responda SOMENTE com JSON, sem texto em volta:
{{"abertura": str, "resumos": {{"<url>": "<resumo>"}}}}
"""


def _sem_cerca(texto: str) -> str:
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def _descrever(blocos: dict[str, list[Oportunidade]]) -> str:
    linhas = []
    for bloco, itens in blocos.items():
        for op in itens:
            marca = " [afirmativa]" if op.afirmativa else ""
            linhas.append(f"- [{bloco}]{marca} {op.titulo} — {op.url}")
    return "\n".join(linhas)


def escrever(
    blocos: dict[str, list[Oportunidade]],
    chamar_modelo: Callable[[str], str],
) -> tuple[str, dict[str, list[Oportunidade]]]:
    """Devolve a abertura e os blocos com resumo preenchido.

    Se o modelo falhar, a edição sai com a abertura padrão e sem resumo — melhor
    uma edição enxuta que nenhuma edição.
    """
    prompt = _MODELO_PROMPT.format(itens=_descrever(blocos))

    try:
        dados = json.loads(_sem_cerca(chamar_modelo(prompt)))
        abertura = (dados.get("abertura") or "").strip() or ABERTURA_PADRAO
        resumos = dados.get("resumos") or {}
    except Exception as erro:
        log.warning("writer falhou, usando abertura padrao: %s", erro)
        return ABERTURA_PADRAO, blocos

    preenchidos = {
        bloco: [
            dataclasses.replace(op, resumo=(resumos.get(op.url) or "").strip())
            for op in itens
        ]
        for bloco, itens in blocos.items()
    }
    return abertura, preenchidos
