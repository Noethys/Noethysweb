# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Nettoyeur (menu Outils) : protection des données (RGPD), allègement de la base de données et des fichiers media.

Pour ajouter une opération :
1. Créer une classe héritant de outils.utils.nettoyeur.base.Operation et implémenter Analyser() et Executer().
2. L'ajouter à la liste OPERATIONS ci-dessous (l'ordre de la liste est l'ordre d'affichage et d'exécution),
   ou la déclarer dans les settings : NETTOYEUR_OPERATIONS_SUPPLEMENTAIRES = ["mon_module.Ma_classe"]
"""

import logging
logger = logging.getLogger(__name__)
from django.conf import settings
from django.utils.module_loading import import_string
from outils.utils.nettoyeur.base import CATEGORIES
from outils.utils.nettoyeur.operations_rgpd import Supprimer_familles, Anonymiser_familles, Effacer_donnees_sante, Desactiver_comptes_portail, \
                                                   Supprimer_contacts, Supprimer_individus_detaches
from outils.utils.nettoyeur.operations_stockage import Supprimer_pieces_remplacees, Supprimer_pieces_expirees, Supprimer_fichiers_orphelins, \
                                                       Supprimer_photos_inactifs, Reduire_images
from outils.utils.nettoyeur.operations_base import Purger_historique, Purger_portail, Purger_emails_sms, Supprimer_paiements_abandonnes


OPERATIONS = [
    # RGPD (la suppression des familles passe avant l'anonymisation)
    Supprimer_familles,
    Anonymiser_familles,
    Effacer_donnees_sante,
    Desactiver_comptes_portail,
    Supprimer_contacts,
    Supprimer_individus_detaches,
    # Stockage
    Supprimer_pieces_remplacees,
    Supprimer_pieces_expirees,
    Supprimer_photos_inactifs,
    # Supprimer_fichiers_orphelins,
    Reduire_images,
    # Base de données
    Purger_historique,
    Purger_portail,
    Purger_emails_sms,
    Supprimer_paiements_abandonnes,
]


def Get_classes_operations():
    classes = list(OPERATIONS)
    for chemin in getattr(settings, "NETTOYEUR_OPERATIONS_SUPPLEMENTAIRES", []):
        try:
            classes.append(import_string(chemin))
        except Exception:
            logger.exception("Nettoyeur : impossible d'importer l'opération %s" % chemin)
    return classes


def Get_operations(cache=None):
    """ Renvoie la liste des opérations instanciées """
    cache = cache if cache is not None else {}
    return [classe(cache=cache) for classe in Get_classes_operations()]


def Get_operation(code=None, cache=None):
    for operation in Get_operations(cache=cache):
        if operation.code == code:
            return operation
    return None


def Get_operations_par_categorie():
    operations = Get_operations()
    return [{"code": code, "label": label, "icone": icone, "operations": [operation for operation in operations if operation.categorie == code]}
            for code, label, icone in CATEGORIES]
