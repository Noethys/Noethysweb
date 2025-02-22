# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from outils.utils.utils_email import Desinscription, Verifie_signature_desinscription


@csrf_exempt
@require_http_methods(["GET"])
def desinscription_emails(request, valeur=None):
    logger.debug("Page DESINSCRIPTION MAILS")
    resultat = Verifie_signature_desinscription(valeur)
    return render(request, "portail/desinscription_emails.html", context={"resultat": resultat, "valeur": valeur})

@csrf_exempt
@require_http_methods(["GET"])
def confirmation_desinscription(request, valeur=None):
    logger.debug("Page CONFIRMATION DESINSCRIPTION MAILS")
    resultat = Desinscription(valeur)
    return render(request, "portail/desinscription_emails.html", context={"resultat": resultat})
