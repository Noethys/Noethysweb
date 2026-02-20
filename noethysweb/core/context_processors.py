# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.conf import settings


def url_root(request):
    """
    Ajoute URL_ROOT au contexte de tous les templates pour permettre
    l'accès à cette variable dans les templates si nécessaire
    """
    return {'URL_ROOT': settings.URL_ROOT}
