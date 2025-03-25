# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, time
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


def Maj_insee_ville_naiss_tous_individus():
    """ Recherche et enregistre les codes INSEE pour les villes de naissance de tous les individus """
    individus = Individu.objects.filter(cp_naiss__isnull=False, ville_naiss__isnull=False, ville_naiss_insee__isnull=True)
    villes = []
    for individu in individus:
        ville = (individu.cp_naiss, individu.ville_naiss)
        if ville not in villes:
            villes.append(ville)

    # Importation des codes INSEE
    from core.utils.utils_adresse import Get_code_insee_ville
    idx = 0
    dict_codes_insee = {}
    for cp, ville in villes:
        dict_codes_insee[(cp, ville)] = Get_code_insee_ville(cp=cp, ville=ville)
        # Pour éviter plafond de 50 requêtes par seconde de l'API Adresse
        if idx > 45:
            time.sleep(2)
            idx = 0
        idx += 1

    # Attribution des codes à chaque individu
    nbre_maj = 0
    for individu in individus:
        ville = (individu.cp_naiss, individu.ville_naiss)
        if dict_codes_insee.get(ville, None):
            individu.ville_naiss_insee = dict_codes_insee[ville]
            individu.save()
            nbre_maj += 1

    return nbre_maj
