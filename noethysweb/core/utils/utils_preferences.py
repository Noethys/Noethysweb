# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

# from core.utils import utils_parametres

def Get_symbole_monnaie():
    return "€"

def Get_code_iso_monnaie():
    """ Code ISO 4217 de la monnaie, utilisé dans les exports comptables et SEPA """
    return "EUR"

def Get_monnaie():
    return {"symbole": "€", "code_iso": "EUR", "singulier": "Euro", "pluriel": "Euros", "division": "Centime"}
