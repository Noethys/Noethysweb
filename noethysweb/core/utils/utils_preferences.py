# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.conf import settings


def Get_symbole_monnaie():
    return getattr(settings, "MONNAIE_SYMBOLE", "€")

def Get_code_iso_monnaie():
    """ Code ISO 4217 de la monnaie, utilisé dans les exports comptables et SEPA """
    return getattr(settings, "MONNAIE_CODE_ISO", "EUR")

def Get_monnaie():
    return {
        "symbole": Get_symbole_monnaie(),
        "code_iso": Get_code_iso_monnaie(),
        "singulier": getattr(settings, "MONNAIE_SINGULIER", "Euro"),
        "pluriel": getattr(settings, "MONNAIE_PLURIEL", "Euros"),
        "division": getattr(settings, "MONNAIE_DIVISION", "Centime"),
    }
