# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import Assurance, Inscription


def Get_assurances_manquantes_famille(famille=None, date_reference=None):
    """ Retourne la liste des assurances obligatoires manquantes pour les individus inscrits de la famille (pour affichage dans le cadre Alertes de la fiche famille) """
    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des inscriptions actuelles de la famille
    conditions = Q(famille=famille) & Q(individu__deces=False) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
    conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=date_reference))
    inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)

    # Recherche des assurances manquantes
    liste_resultats = []
    for individu in Get_assurances_manquantes_by_inscriptions(famille=famille, inscriptions=inscriptions):
        liste_resultats.append({
            "label": "Assurance de %s" % (individu.prenom or individu.nom),
            "valide": False,
            "titre": "Cliquez ici pour accéder à la page des assurances de l'individu",
            "href": reverse_lazy("individu_assurances_liste", kwargs={"idfamille": famille.pk, "idindividu": individu.pk}),
        })

    return liste_resultats


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
