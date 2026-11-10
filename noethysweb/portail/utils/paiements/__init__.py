# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Paiement en ligne du portail famille.
    Chaque système de paiement est un module exposant :
      - Creer_paiement(request, demande, parametres_portail) -> JsonResponse
      - sa ou ses vues de notification (déclarées dans portail/urls.py) """

import importlib

SYSTEMES = ("demo", "payfip", "payzen", "helloasso")


def Get_systeme(code=None):
    """ Renvoie le module du système de paiement ou None """
    if code not in SYSTEMES:
        return None
    return importlib.import_module("portail.utils.paiements.%s" % code)
