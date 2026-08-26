"""Renderização do HTML da edição.

CSS é inline por exigência de cliente de email: nada de folha externa nem
@import, que Gmail e Outlook descartam.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsletter import config
from newsletter.models import Oportunidade

TEMPLATES = Path(__file__).parent / "templates"

# Tag que o Brevo troca pelo link real de descadastro no momento do envio.
UNSUBSCRIBE_BREVO = "{{ unsubscribe }}"


def renderizar(
    abertura: str, blocos: dict[str, list[Oportunidade]], semana: str
) -> str:
    """Monta o HTML completo da edição."""
    ambiente = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = ambiente.get_template("edicao.html.j2")
    return template.render(
        abertura=abertura,
        blocos=blocos,
        semana=semana,
        logo_url=config.LOGO_URL,
        form_url=config.FORM_BASE_TALENTOS_URL,
        instagram_url=config.INSTAGRAM_URL,
        linkedin_url=config.LINKEDIN_URL,
        roxo=config.ROXO,
        amarelo=config.AMARELO,
        marrom=config.MARROM,
        preto=config.PRETO,
        unsubscribe=UNSUBSCRIBE_BREVO,
    )
