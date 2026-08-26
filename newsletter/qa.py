"""Análise da edição pronta, antes de ela virar rascunho.

Duas camadas, de propósito:

1. **Verificações locais** — ano passado no título, prazo vencido, prazo
   ausente, título genérico, URL repetida. São determinísticas: código faz isso
   melhor que modelo, sempre igual e sem gastar cota.
2. **Parecer do modelo** — o que código não pega: item que parece publicidade,
   título que não diz de quem é a vaga, incoerência entre título e resumo.

É um **alerta, não um portão**: o resultado vai no email de aviso para quem
revisa saber onde olhar. Nada aqui bloqueia a criação do rascunho — a decisão de
enviar continua sendo de uma pessoa.
"""

import datetime
import json
import logging
import re
from collections.abc import Callable

from newsletter.models import Oportunidade

log = logging.getLogger(__name__)

# Abaixo disto o título não identifica a oportunidade ("Gestão", "Qualifica SP").
MIN_PALAVRAS_TITULO = 4

PROMPT = """Você revisa a edição da newsletter do Clube dos Libertos antes de ela
ir para revisão humana. Hoje é {hoje}.

Aponte só problemas concretos, olhando cada item:
- parece publicidade, artigo ou vídeo em vez de oportunidade com inscrição aberta;
- o título não diz de qual organização é a oportunidade;
- o resumo afirma coisa que o título contradiz;
- a oportunidade parece encerrada ou de edição antiga.

Itens:
{itens}

Responda SOMENTE com JSON:
{{"problemas": [str], "parecer": str}}

`problemas`: uma frase por item problemático, começando pelo título dele. Lista
vazia se não houver nenhum. `parecer`: uma frase sobre a edição como um todo.
"""


def verificacoes_locais(
    itens: list[Oportunidade], hoje: datetime.date
) -> list[str]:
    """O que dá para checar sem modelo nenhum."""
    achados: list[str] = []
    vistas: dict[str, str] = {}

    for op in itens:
        anos = {int(a) for a in re.findall(r"\b20\d\d\b", op.titulo)}
        passados = sorted(a for a in anos if a < hoje.year)
        if passados and not any(a >= hoje.year for a in anos):
            achados.append(
                f"{op.titulo[:60]!r}: título cita {passados[0]}, ano já passado"
            )

        if op.prazo is None:
            achados.append(f"{op.titulo[:60]!r}: sem prazo de inscrição")
        elif op.prazo < hoje:
            achados.append(
                f"{op.titulo[:60]!r}: prazo vencido em {op.prazo.strftime('%d/%m/%Y')}"
            )

        if len(op.titulo.split()) < MIN_PALAVRAS_TITULO:
            achados.append(
                f"{op.titulo[:60]!r}: título genérico, não identifica a organização"
            )

        if op.url in vistas:
            achados.append(f"{op.titulo[:60]!r}: URL repetida, igual a {vistas[op.url][:40]!r}")
        else:
            vistas[op.url] = op.titulo

    return achados


def _descrever(itens: list[Oportunidade]) -> str:
    return "\n".join(
        f"- {op.titulo} | categoria: {op.categoria} | fonte: {op.fonte} | "
        f"prazo: {op.prazo.isoformat() if op.prazo else 'nenhum'}\n"
        f"  resumo: {op.resumo}"
        for op in itens
    )


def analisar(
    itens: list[Oportunidade],
    hoje: datetime.date,
    chamar_modelo: Callable[[str], str],
) -> dict:
    """Devolve achados locais e o parecer do modelo."""
    resultado = {
        "locais": verificacoes_locais(itens, hoje),
        "problemas": [],
        "parecer": "",
        "erro": None,
    }

    try:
        texto = chamar_modelo(
            PROMPT.format(hoje=hoje.isoformat(), itens=_descrever(itens))
        )
        limpo = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE)
        dados = json.loads(limpo.strip())
        resultado["problemas"] = [str(p) for p in (dados.get("problemas") or [])]
        resultado["parecer"] = str(dados.get("parecer") or "")
    except Exception as erro:
        log.warning("analise pelo modelo falhou: %s", erro)
        resultado["erro"] = str(erro)

    return resultado


def formatar_relatorio(resultado: dict, total: int) -> str:
    """Texto do relatório que vai no email de aviso."""
    linhas = [f"ANALISE DA EDICAO ({total} itens)", ""]

    achados = resultado.get("locais") or []
    problemas = resultado.get("problemas") or []

    if not achados and not problemas:
        linhas.append("Nenhum problema encontrado.")
    else:
        if achados:
            linhas.append(f"Verificacoes automaticas ({len(achados)}):")
            linhas += [f"  - {a}" for a in achados]
            linhas.append("")
        if problemas:
            linhas.append(f"Apontado pela IA ({len(problemas)}):")
            linhas += [f"  - {p}" for p in problemas]
            linhas.append("")

    if resultado.get("parecer"):
        linhas.append(f"Parecer geral: {resultado['parecer']}")
    if resultado.get("erro"):
        linhas.append(f"(a analise pela IA falhou: {resultado['erro']})")

    return "\n".join(linhas)
