# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.conf import settings
from core.utils import utils_preferences


def url_root(request):
    """
    Ajoute URL_ROOT au contexte de tous les templates pour permettre
    l'accès à cette variable dans les templates si nécessaire
    """
    return {'URL_ROOT': settings.URL_ROOT}


def monnaie(request):
    """
    Ajoute le symbole monétaire courant au contexte de tous les templates,
    pour l'utiliser notamment dans les portions de code Javascript qui ne
    passent pas par le filtre de template "montant"
    """
    return {'SYMBOLE_MONNAIE': utils_preferences.Get_symbole_monnaie()}
