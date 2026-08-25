"""Aviso de execução por email transacional do Brevo.

Mesmo canal para sucesso e para falha, de modo que silêncio signifique sempre
"o job não rodou".
"""

import logging

from newsletter.config import REMETENTE_EMAIL, REMETENTE_NOME
from newsletter.publisher import _postar

log = logging.getLogger(__name__)

API_TRANSACIONAL = "https://api.brevo.com/v3/smtp/email"


def avisar(assunto: str, corpo: str, api_key: str, poster=None) -> None:
    """Envia o aviso. Falhar em avisar não derruba a execução."""
    postar = poster or _postar
    try:
        postar(
            API_TRANSACIONAL,
            {"api-key": api_key, "accept": "application/json"},
            {
                "sender": {"name": REMETENTE_NOME, "email": REMETENTE_EMAIL},
                "to": [{"email": REMETENTE_EMAIL}],
                "subject": assunto,
                "htmlContent": f"<pre style='font-family:monospace'>{corpo}</pre>",
            },
        )
    except Exception as erro:
        log.warning("nao foi possivel enviar o aviso: %s", erro)
