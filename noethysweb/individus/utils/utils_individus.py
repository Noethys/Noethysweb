# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Famille, Individu, Rattachement
from core.utils import utils_texte
from django.db.models import Q


def Maj_infos_toutes_familles():
    """ Met à jour les noms des titulaires et adresses de toutes les familles """
    logger.debug("MAJ des infos de toutes les familles...")
    for famille in Famille.objects.all():
        famille.Maj_infos()
    logger.debug("Fin de la MAJ des infos.")

def Maj_infos_tous_individus():
    """ Met à jour les adresses de tous les individus """
    logger.debug("MAJ des infos de tous les individus...")
    for individu in Individu.objects.all():
        individu.Maj_infos()
    logger.debug("Fin de la MAJ des infos.")
