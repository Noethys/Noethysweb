# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Utilitaire d'intégration de l'API HelloAsso (paiement en ligne "Checkout Intent") """

import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

URLS = {
    "sandbox": {
        "api": "https://api.helloasso-sandbox.com",
        "token": "https://api.helloasso-sandbox.com/oauth2/token",
    },
    "production": {
        "api": "https://api.helloasso.com",
        "token": "https://api.helloasso.com/oauth2/token",
    },
}


class ErreurHelloasso(Exception):
    pass


def Get_mode(parametres_portail={}):
    return parametres_portail.get("helloasso_mode") or "sandbox"


def Get_access_token(parametres_portail={}):
    """ Récupère un jeton d'accès OAuth2 (client_credentials), en le mettant en cache jusqu'à expiration """
    mode = Get_mode(parametres_portail)
    client_id = parametres_portail.get("helloasso_client_id")
    cle_cache = "helloasso_access_token_%s_%s" % (mode, client_id)

    token = cache.get(cle_cache)
    if token:
        return token

    reponse = requests.post(URLS[mode]["token"], data={
        "client_id": client_id,
        "client_secret": parametres_portail.get("helloasso_client_secret"),
        "grant_type": "client_credentials",
    }, timeout=15)

    if reponse.status_code != 200:
        logger.error("Erreur HelloAsso lors de la récupération du token : %s %s", reponse.status_code, reponse.text)
        raise ErreurHelloasso("Impossible de s'authentifier auprès d'HelloAsso.")

    data = reponse.json()
    token = data["access_token"]

    # Mise en cache du token, avec une marge de sécurité d'une minute avant expiration
    duree_validite = int(data.get("expires_in", 1800)) - 60
    cache.set(cle_cache, token, timeout=max(duree_validite, 60))

    return token


def Appel_api(parametres_portail={}, methode="GET", chemin="", donnees=None):
    """ Effectue un appel authentifié à l'API HelloAsso v5 """
    mode = Get_mode(parametres_portail)
    token = Get_access_token(parametres_portail=parametres_portail)
    url = "%s%s" % (URLS[mode]["api"], chemin)
    headers = {"Authorization": "Bearer %s" % token}

    reponse = requests.request(methode, url, json=donnees, headers=headers, timeout=15)

    if reponse.status_code not in (200, 201):
        logger.error("Erreur HelloAsso lors de l'appel %s %s : %s %s", methode, chemin, reponse.status_code, reponse.text)
        raise ErreurHelloasso("Erreur lors de la communication avec HelloAsso (code %d)." % reponse.status_code)

    return reponse.json()


def Creer_checkout_intent(parametres_portail={}, montant=None, email=None, item_name="", back_url="", error_url="", return_url="", metadata=None):
    """ Crée une intention de paiement (Checkout Intent) et renvoie la réponse de l'API (id + redirectUrl) """
    slug = parametres_portail.get("helloasso_organisation_slug")

    corps = {
        "totalAmount": int(round(float(montant) * 100)),
        "initialAmount": int(round(float(montant) * 100)),
        "itemName": item_name,
        "backUrl": back_url,
        "errorUrl": error_url,
        "returnUrl": return_url,
        "containsDonation": False,
    }
    if email:
        corps["payer"] = {"email": email}
    if metadata is not None:
        corps["metadata"] = metadata

    return Appel_api(parametres_portail=parametres_portail, methode="POST", chemin="/v5/organizations/%s/checkout-intents" % slug, donnees=corps)


def Get_checkout_intent(parametres_portail={}, checkout_intent_id=None):
    """ Récupère l'état d'une intention de paiement (utilisé pour vérifier une notification avant de l'appliquer) """
    slug = parametres_portail.get("helloasso_organisation_slug")
    return Appel_api(parametres_portail=parametres_portail, methode="GET", chemin="/v5/organizations/%s/checkout-intents/%s" % (slug, checkout_intent_id))
