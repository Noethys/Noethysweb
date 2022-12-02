# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Famille, Individu, Cotisation, Rattachement, TarifLigne, Prestation


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

def Maj_lignes_tarifs_prestations():
    """ Met à jour les tarif_ligne dans chaque prestation """
    logger.debug("MAJ des lignes de tarifs dans les prestations...")

    # Importation des lignes de tarifs existantes
    dict_lignes = {}
    for ligne in TarifLigne.objects.all().order_by("num_ligne"):
        dict_lignes.setdefault(ligne.tarif_id, [])
        dict_lignes[ligne.tarif_id].append(ligne)

    # MAJ des prestations
    liste_modifications = []
    prestations = Prestation.objects.select_related("tarif").filter(tarif_ligne__isnull=True, tarif__isnull=False)
    logger.debug("Nbre prestations trouvées : %s" % len(prestations))
    for prestation in prestations:
        # Recherche une ligne de tarif correspondant au montant
        for ligne in dict_lignes.get(prestation.tarif_id, []):
            if not prestation.quantite:
                prestation.quantite = 1
            if ligne.montant_unique and (ligne.montant_unique * prestation.quantite == prestation.montant_initial or (prestation.tarif.penalite_pourcentage and ligne.montant_unique * prestation.tarif.penalite_pourcentage / 100) * prestation.quantite == prestation.montant_initial):
                prestation.tarif_ligne = ligne
                liste_modifications.append(prestation)
                break
    logger.debug("Modification de %d prestations..." % len(liste_modifications))
    Prestation.objects.bulk_update(liste_modifications, ["tarif_ligne"], batch_size=50)
    logger.debug("Fin de la MAJ des lignes de tarifs.")
