# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Historique


def Ajouter(titre="", detail="", utilisateur=None, famille=None, individu=None, objet=None, idobjet=None, classe=None, old=None, portail=False):
    try:
        Historique.objects.create(titre=titre, detail=detail, utilisateur=utilisateur, famille_id=famille,
                                  individu_id=individu, objet=objet, idobjet=idobjet, classe=classe, old=old, portail=portail)
    except Exception as err:
        logger.error("Erreur dans ajout historique : %s" % err)


def Ajouter_plusieurs(actions=[]):
    liste_ajouts = [Historique(**action) for action in actions]
    Historique.objects.bulk_create(liste_ajouts)
