# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Famille, Individu, Cotisation, Rattachement


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

def Maj_cotisations_individuelles():
    """ Associe l'IDfamille à toutes cotisations individuelles sans IDfamille """
    logger.debug("MAJ des cotisations individuelles...")
    cotisations = Cotisation.objects.select_related("prestation").filter(famille_id__isnull=True)
    for cotisation in cotisations:
        idfamille = None
        if cotisation.prestation:
            idfamille = cotisation.prestation.famille_id
        else:
            rattachement = Rattachement.objects.filter(individu_id=cotisation.individu_id).first()
            if rattachement:
                idfamille = rattachement.famille_id
        if idfamille:
            cotisation.famille_id = idfamille
            cotisation.save()
    logger.debug("Fin de la MAJ des cotisations individuelles.")
