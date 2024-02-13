# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


def Maj_infos():
    """ Met à jour des infos dans la DB """
    from individus.utils import utils_individus
    from reglements.utils import utils_depots
    from facturation.utils import utils_factures

    # MAJ des noms et des adresses des familles
    utils_individus.Maj_infos_toutes_familles()

    # Met à jour les adresses de tous les individus
    utils_individus.Maj_infos_tous_individus()

    # Ajoute l'IDfamille aux cotisations individuelles
    utils_individus.Maj_cotisations_individuelles()

    # Met à jour les tarif_ligne dans chaque prestation
    utils_individus.Maj_lignes_tarifs_prestations()

    # Met à jour les montants des dépôts
    utils_depots.Maj_montant_depots()

    # Met à jour les totaux des factures
    utils_factures.Maj_total_factures(IDfamille=0, IDfacture=0)

