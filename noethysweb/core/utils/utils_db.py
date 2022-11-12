# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


def Maj_infos():
    """ Met à jour des infos dans la DB """
    from individus.utils import utils_individus

    # MAJ des noms et des adresses des familles
    utils_individus.Maj_infos_toutes_familles()

    # Met à jour les adresses de tous les individus
    utils_individus.Maj_infos_tous_individus()

    # Ajoute l'IDfamille aux cotisations individuelles
    utils_individus.Maj_cotisations_individuelles()
