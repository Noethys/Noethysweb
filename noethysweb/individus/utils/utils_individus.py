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



# def GetTitulaires(liste_idfamilles=[], avec_civilite=False, avec_adresse=False):
#     dict_resultats = {}
#
#     condition = Q(categorie=1) & Q(titulaire=True)
#     if liste_idfamilles:
#         condition &= Q(famille_id__in=liste_idfamilles)
#     rattachements = Rattachement.objects.prefetch_related('individu').filter(condition).order_by("individu__civilite")
#
#     dict_rattachements = {}
#     for rattachement in rattachements:
#         dict_rattachements.setdefault(rattachement.famille_id, [])
#         dict_rattachements[rattachement.famille_id].append(rattachement)
#
#     for idfamille, rattachements_famille in dict_rattachements.items():
#
#         # Cherche si les noms de famille sont identiques
#         dict_noms = {}
#         for rattachement in rattachements_famille:
#             if rattachement.individu.nom not in dict_noms:
#                 dict_noms[rattachement.individu.nom] = []
#             dict_noms[rattachement.individu.nom].append(rattachement.individu.prenom)
#
#         nom_titulaires = ""
#         if len(dict_noms) == 1:
#             for nom, liste_prenoms in dict_noms.items():
#                 nom_titulaires = nom + " " + utils_texte.Convert_liste_to_texte_virgules(liste_prenoms)
#         else:
#             liste_noms = [rattachement.individu.Get_nom(avec_civilite=avec_civilite) for rattachement in rattachements_famille]
#             nom_titulaires = utils_texte.Convert_liste_to_texte_virgules(liste_noms)
#
#         dict_resultats[idfamille] = {"nom": nom_titulaires}
#         if avec_adresse:
#             dict_resultats[idfamille]["adresse"] = rattachements_famille[0].individu.Get_adresse(individu=rattachements_famille[0].individu)
#
#     return dict_resultats
