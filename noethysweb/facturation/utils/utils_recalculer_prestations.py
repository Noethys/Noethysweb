# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.db.models import Q, Count
from core.models import Prestation
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle


def Recalculer(request=None, date_debut=None, date_fin=None):
    # Recherche les prestations de la période
    condition = Q(date__gte=date_debut, date__lte=date_fin, categorie="consommation", activite__isnull=False)
    prestations = Prestation.objects.filter(condition).values("famille_id", "individu_id", "activite_id").annotate(nbre_prestations=Count("idprestation"))

    # Recalcul dans la grille virtuelle
    logger.debug("Lancement procédure de recalcul des prestations %s > %s ..." % (date_debut, date_fin))
    for prestation in prestations:
        logger.debug("Recalculer des prestations : famille ID%d | individu ID%d | activite ID%d" % (prestation["famille_id"], prestation["individu_id"], prestation["activite_id"]))
        grille = Grille_virtuelle(request=request, idfamille=prestation["famille_id"], idindividu=prestation["individu_id"], idactivite=prestation["activite_id"], date_min=date_debut, date_max=date_fin)
        grille.Recalculer_tout()
        grille.Enregistrer()
    logger.debug("Fin de la procédure de recalcul des prestations.")
