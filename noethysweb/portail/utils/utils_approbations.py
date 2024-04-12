# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from dateutil import relativedelta
from django.db.models import Q
from core.models import TypeConsentement, UniteConsentement, Consentement, Inscription, Rattachement, PortailParametre


def Get_approbations_requises(famille=None, activites=None, idindividu=None, avec_consentements_existants=True):
    """ activites = Une liste d'activités. Si vide, on recherche les inscriptions de la famille """
    approbations_requises = {"consentements": [], "rattachements": [], "familles": [], "nbre_total": 0}

    # Recherche des inscriptions actives de la famille
    if not activites:
        conditions = Q(famille=famille) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        inscriptions = Inscription.objects.select_related("activite", "individu").prefetch_related('activite__types_consentements').filter(conditions)
        activites = list({inscription.activite: True for inscription in inscriptions}.keys())

    # Recherche des types de consentements nécessaires
    types_consentements = []
    for activite in activites:
        for type_consentement in activite.types_consentements.all():
            if type_consentement not in types_consentements:
                types_consentements.append(type_consentement)

    # Recherche les unités de consentements actuelles
    conditions = Q(type_consentement__in=types_consentements) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
    unites_consentements = {unite.type_consentement: unite for unite in UniteConsentement.objects.select_related("type_consentement").filter(conditions).order_by("date_debut")}

    # Recherche des consentements existants de la famille
    if avec_consentements_existants:
        consentements_famille = Consentement.objects.select_related("unite_consentement").filter(famille=famille, unite_consentement__in=unites_consentements.values()).order_by("horodatage")
        unites_consentements_famille = [consentement.unite_consentement for consentement in consentements_famille]
    else:
        unites_consentements_famille = []

    # Mémorisation des consentements requis
    for type_consentement, unite_consentement in unites_consentements.items():
        if unite_consentement not in unites_consentements_famille:
            approbations_requises["consentements"].append(unite_consentement)

    # Importation de la durée de validité d'une certification
    duree_certification_defaut = PortailParametre.objects.filter(code="renseignements_duree_certification")
    duree_certification = duree_certification_defaut.first().valeur if duree_certification_defaut else None

    # Recherche des approbations des rattachements
    rattachements = Rattachement.objects.prefetch_related('individu').filter(famille=famille).exclude(individu__in=famille.individus_masques.all()).order_by("individu__nom", "individu__prenom")
    for rattachement in rattachements:
        if not idindividu or rattachement.individu_id == idindividu or rattachement.categorie == 1:
            if Get_etat_certification(rattachement.certification_date, duree_certification) != "VALIDE":
                approbations_requises["rattachements"].append(rattachement)

    # Recherche des approbations de la fiche famille
    if Get_etat_certification(famille.certification_date, duree_certification) != "VALIDE":
        approbations_requises["familles"].append(famille)

    # Calcul le nombre d'approbations total
    approbations_requises["nbre_total"] = len(approbations_requises["consentements"]) + len(approbations_requises["rattachements"]) + len(approbations_requises["familles"])

    return approbations_requises

def Get_etat_certification(date_certification=None, duree_certification=None):
    if not date_certification:
        return "NON_VALIDE"
    if duree_certification:
        type_validite, parametre = duree_certification.split("_")
        if type_validite == "DUREE":
            if datetime.date.today() > date_certification.date() + relativedelta.relativedelta(months=+int(parametre)):
                return "EXPIRE"
        if type_validite == "DATE":
            date_fin_validite = date_certification.date() + relativedelta.relativedelta(day=1, month=int(parametre))
            if date_fin_validite < date_certification.date():
                date_fin_validite += relativedelta.relativedelta(years=+1)
            if datetime.date.today() > date_fin_validite:
                return "EXPIRE"
    return "VALIDE"
