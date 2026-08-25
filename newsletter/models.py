"""Modelo de dados central do pipeline da newsletter."""

import datetime
from dataclasses import dataclass

CATEGORIAS = ("trainee", "estagio", "edital", "educacao")

_BLOCOS = {
    "trainee": "Trainees e estágios",
    "estagio": "Trainees e estágios",
    "edital": "Editais e formações",
    "educacao": "Editais e formações",
}


@dataclass(frozen=True)
class Oportunidade:
    titulo: str
    url: str
    categoria: str
    fonte: str
    prazo: datetime.date | None
    afirmativa: bool
    resumo: str = ""


def bloco_de(categoria: str) -> str:
    """Devolve o bloco da edição em que a categoria aparece."""
    try:
        return _BLOCOS[categoria]
    except KeyError:
        raise ValueError(f"categoria desconhecida: {categoria!r}") from None
