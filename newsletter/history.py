"""Histórico de oportunidades já publicadas, versionado no próprio repositório."""

import datetime
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from newsletter.models import Oportunidade

# Parâmetros de rastreamento que não mudam o destino do link.
_PARAMS_DESCARTAVEIS = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


def chave(url: str) -> str:
    """Normaliza a URL para servir de chave de deduplicação."""
    partes = urlsplit(url.strip())
    query = [
        (nome, valor)
        for nome, valor in parse_qsl(partes.query)
        if not nome.lower().startswith(_PARAMS_DESCARTAVEIS)
    ]
    caminho = partes.path.rstrip("/")
    return urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), caminho, urlencode(query), "")
    )


def carregar(caminho: str | Path) -> set[str]:
    """Devolve as chaves já publicadas. Arquivo inexistente é histórico vazio."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        return set()
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return {item["chave"] for item in dados.get("itens", [])}


def registrar(
    caminho: str | Path,
    oportunidades: list[Oportunidade],
    data_edicao: datetime.date,
) -> None:
    """Acrescenta as oportunidades ao histórico, preservando o conteúdo anterior."""
    arquivo = Path(caminho)
    if arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    else:
        dados = {"itens": []}

    for op in oportunidades:
        dados["itens"].append(
            {
                "chave": chave(op.url),
                "titulo": op.titulo,
                "url": op.url,
                "data_edicao": data_edicao.isoformat(),
            }
        )

    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
