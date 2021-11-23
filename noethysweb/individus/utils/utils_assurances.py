# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from core.models import Assurance


def Get_assurances_manquantes_by_inscriptions(famille=None, inscriptions=None):
    # Recherche les individus pour qui l'assurance est obligatoire
    liste_individus = []
    for inscription in inscriptions:
        if inscription.activite.assurance_obligatoire and inscription.individu not in liste_individus:
            liste_individus.append(inscription.individu)

    # Recherche les assurances existantes
    dict_assurances = {}
    conditions = Q(famille=famille) & Q(individu_id__in=liste_individus) & Q(date_debut__lte=datetime.date.today()) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
    for assurance in Assurance.objects.select_related("individu").filter(conditions):
        dict_assurances.setdefault(assurance.individu, [])
        dict_assurances[assurance.individu].append(assurance)

    # Recherche les assurances manquantes
    resultats = [individu for individu in liste_individus if individu not in dict_assurances]

    return resultats
