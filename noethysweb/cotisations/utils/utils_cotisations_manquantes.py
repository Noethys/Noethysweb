# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import Cotisation, Inscription
from core.utils import utils_texte


def Get_cotisations_manquantes(famille=None, date_reference=None, utilisateur=None, exclure_individus=[]):
    """ Retourne les cotisations manquantes d'une famille """
    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des inscriptions
    conditions = Q(famille=famille) & Q(individu__deces=False) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
    if utilisateur:
        conditions &= Q(activite__structure__in=utilisateur.structures.all())

    # Lecture de la db
    inscriptions = Inscription.objects.select_related('activite', 'individu', 'famille').prefetch_related('activite__cotisations').filter(conditions).exclude(individu__in=exclure_individus).distinct()
    cotisations_existantes = Cotisation.objects.select_related('type_cotisation').filter(Q(famille=famille, date_debut__lte=date_reference, date_fin__gte=date_reference))

    dict_cotisations = {}
    for cotisation in cotisations_existantes:
        if cotisation.type_cotisation.type == "famille":
            key = "famille_%d_%d" % (cotisation.famille_id, cotisation.type_cotisation_id)
        else:
            key = "individu_%d_%d" % (cotisation.individu_id, cotisation.type_cotisation_id)
        dict_cotisations.setdefault(key, [])
        dict_cotisations[key].append(cotisation)

    liste_traitees = []
    liste_resultats = []
    for inscription in inscriptions:
        # Recherche au moins une cotisation existante pour cette inscription
        valide = False
        for type_cotisation in inscription.activite.cotisations.all():
            # Vérifie si la cotisation existe
            if type_cotisation.type == "famille":
                key = "famille_%d_%d" % (inscription.famille_id, type_cotisation.pk)
            else:
                key = "individu_%d_%d" % (inscription.individu_id, type_cotisation.pk)
            for cotisation in dict_cotisations.get(key, []):
                if type_cotisation.type == "famille":
                    valide = True
                if type_cotisation.type == "individu" and cotisation.individu_id == inscription.individu_id:
                    valide = True

        if not valide:
            for type_cotisation in inscription.activite.cotisations.all():
                # Création du label
                if type_cotisation.type == "famille":
                    label = type_cotisation.nom
                else:
                    label = "%s de %s" % (type_cotisation.nom, inscription.individu.prenom)

                # Création du lien de création rapide
                href = reverse_lazy("famille_cotisations_saisie_rapide", kwargs={'idfamille': inscription.famille_id, 'idtype_cotisation': type_cotisation.pk, 'idindividu': inscription.individu_id})

                # Mémorise la cotisation à fournir
                dict_temp = {
                    "label": label,
                    "valide": False,
                    "type_cotisation": type_cotisation,
                    "titre": "Cliquez ici pour créer immédiatement cette adhésion",
                    "href": href,
                }
                if type_cotisation.type == "famille":
                    dict_temp["individu"] = None
                    temp = (type_cotisation, None, inscription.famille_id)
                else:
                    dict_temp["individu"] = inscription.individu
                    temp = (type_cotisation, inscription.individu, inscription.famille_id)
                if temp not in liste_traitees:
                    liste_traitees.append(temp)
                    liste_resultats.append(dict_temp)

    return liste_resultats


def Get_liste_cotisations_manquantes(date_reference=None, activites=None, presents=None, only_concernes=True):
    """ Retourne les cotisations manquantes d'un ensemble de familles inscrites ou présentes """
    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des inscriptions
    conditions = Q()
    if activites:
        conditions &= Q(activite__in=activites)
    if presents:
        conditions &= Q(consommation__date__gte=presents[0], consommation__date__lte=presents[1])
    inscriptions = Inscription.objects.select_related('activite', 'individu', 'famille').prefetch_related('activite__cotisations').filter(conditions).distinct()

    # Importation des cotisations existantes
    conditions = Q(date_debut__lte=date_reference, date_fin__gte=date_reference)
    cotisations_existantes = Cotisation.objects.select_related('type_cotisation').filter(conditions)

    dict_cotisations = {}
    for cotisation in cotisations_existantes:
        if cotisation.type_cotisation.type == "famille":
            key = "famille_%d_%d" % (cotisation.famille_id, cotisation.type_cotisation_id)
        else:
            key = "individu_%d_%d" % (cotisation.individu_id, cotisation.type_cotisation_id)
        dict_cotisations.setdefault(key, [])
        dict_cotisations[key].append(cotisation)

    liste_traitees = []
    dict_resultats = {}
    for inscription in inscriptions:
        dict_resultats.setdefault(inscription.famille, [])

        # Recherche au moins une cotisation existante pour cette inscription
        valide = False
        for type_cotisation in inscription.activite.cotisations.all():
            # Vérifie si la cotisation existe
            if type_cotisation.type == "famille":
                key = "famille_%d_%d" % (inscription.famille_id, type_cotisation.pk)
            else:
                key = "individu_%d_%d" % (inscription.individu_id, type_cotisation.pk)
            for cotisation in dict_cotisations.get(key, []):
                if type_cotisation.type == "famille" and cotisation.famille_id == inscription.famille_id:
                    valide = True
                if type_cotisation.type == "individu" and cotisation.individu_id == inscription.individu_id:
                    if cotisation.famille_id == inscription.famille_id:
                        valide = True

        if not valide:
            for type_cotisation in inscription.activite.cotisations.all():
                # Création du label
                if type_cotisation.type == "famille":
                    label = type_cotisation.nom
                else:
                    label = "%s de %s" % (type_cotisation.nom, inscription.individu.prenom)

                # Mémorise la pièce à fournir
                dict_temp = {
                    "label": label,
                    "valide": valide,
                    "type_cotisation": type_cotisation,
                    "titre": "Cliquez ici pour créer immédiatement cette adhésion",
                }
                if type_cotisation.type == "famille":
                    dict_temp["individu"] = None
                    temp = (type_cotisation, None, inscription.famille_id)
                else:
                    dict_temp["individu"] = inscription.individu
                    temp = (type_cotisation, inscription.individu, inscription.famille_id)
                if temp not in liste_traitees and not valide:
                    liste_traitees.append(temp)
                    dict_resultats[inscription.famille].append(dict_temp)

    # Tri et filtre des résultats
    dict_final = {}
    for famille, liste_cotisations in dict_resultats.items():
        if not only_concernes or liste_cotisations:
            liste_cotisations = sorted(liste_cotisations, key=lambda x: x["label"])
            texte = utils_texte.Convert_liste_to_texte_virgules([x["label"] for x in liste_cotisations])
            dict_final[famille.pk] = {"texte": texte, "nbre": len(liste_cotisations), "liste": liste_cotisations, "nom_famille": famille.nom}

    return dict_final
