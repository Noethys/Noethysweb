# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Historique


def Ajouter(titre="", detail="", utilisateur=None, famille=None, individu=None, objet=None, idobjet=None, classe=None):
    try:
        Historique.objects.create(titre=titre, detail=detail, utilisateur=utilisateur, famille_id=famille,
                                  individu_id=individu, objet=objet, idobjet=idobjet, classe=classe)
    except:
        pass

def Ajouter_plusieurs(actions=[]):
    liste_ajouts = [Historique(**action) for action in actions]
    Historique.objects.bulk_create(liste_ajouts)
