# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Historique


def Ajouter(titre="", detail="", utilisateur=None, famille=None, individu=None):
    Historique.objects.create(titre=titre, detail=detail, utilisateur=utilisateur, famille_id=famille, individu_id=individu)
