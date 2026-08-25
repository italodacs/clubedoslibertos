"""Criação da campanha em rascunho no Brevo. Nunca dispara envio."""

import logging

import requests

from newsletter.config import REMETENTE_EMAIL, REMETENTE_NOME

log = logging.getLogger(__name__)

API_CAMPANHAS = "https://api.brevo.com/v3/emailCampaigns"
URL_CAMPANHA = "https://app.brevo.com/campaign/classic/edit/{id}"
TIMEOUT = 30


def _postar(url: str, cabecalhos: dict, corpo: dict) -> dict:
    resposta = requests.post(url, headers=cabecalhos, json=corpo, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json() if resposta.content else {}


def criar_rascunho(
    html: str,
    assunto: str,
    lista_id: int,
    api_key: str,
    poster=None,
) -> int:
    """Cria a campanha como rascunho e devolve o id.

    Falha propaga de propósito: quem orquestra precisa salvar o HTML e avisar,
    em vez de perder a edição em silêncio.
    """
    postar = poster or _postar
    corpo = {
        "name": assunto,
        "subject": assunto,
        "sender": {"name": REMETENTE_NOME, "email": REMETENTE_EMAIL},
        "htmlContent": html,
        "recipients": {"listIds": [lista_id]},
    }
    resposta = postar(
        API_CAMPANHAS, {"api-key": api_key, "accept": "application/json"}, corpo
    )
    campanha_id = resposta["id"]
    log.info("campanha rascunho criada: %s", URL_CAMPANHA.format(id=campanha_id))
    return campanha_id
