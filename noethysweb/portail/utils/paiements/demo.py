# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne : mode démo (aucun paiement réel) """

import logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse


def Creer_paiement(request=None, demande=None, parametres_portail={}):
    logger.debug("Paiement en ligne MODE DEMO (Famille %s) : montant=%s ventilation=%s", demande.famille, demande.montant, demande.ventilation_str)
    return JsonResponse({"systeme_paiement": "demo", "texte": "Paiement impossible, vous êtes en mode démo !"})
