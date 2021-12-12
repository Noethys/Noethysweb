# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from core.models import TypeMaladie, Vaccin, Individu
from core.utils import utils_dates


def Get_vaccins_obligatoires_individu(individu=None, nonvalides_only=False):
    liste_resultats = []
    vaccins = Vaccin.objects.select_related("type_vaccin").prefetch_related("type_vaccin__types_maladies").filter(individu=individu)
    for maladie in TypeMaladie.objects.filter(vaccin_obligatoire=True).order_by("nom"):
        if not individu.date_naiss or not maladie.vaccin_date_naiss_min or (maladie.vaccin_date_naiss_min and individu.date_naiss >= maladie.vaccin_date_naiss_min):
            valide = False
            for vaccin in vaccins:
                if maladie in vaccin.type_vaccin.types_maladies.all():
                    if vaccin.type_vaccin.duree_validite:
                        date_fin_validite = vaccin.date + utils_dates.ConvertDureeStrToDuree(vaccin.type_vaccin.duree_validite)
                        if date_fin_validite >= datetime.date.today():
                            valide = True
                    else:
                        valide = True
            if not nonvalides_only or (nonvalides_only and not valide):
                liste_resultats.append({"label": maladie.nom, "valide": valide})
    return liste_resultats


def Get_vaccins_obligatoires_by_inscriptions(inscriptions=None):
    # Recherche les individus pour qui les vaccinations sont obligatoires
    liste_individus = []
    for inscription in inscriptions:
        if inscription.activite.vaccins_obligatoires and inscription.individu not in liste_individus:
            liste_individus.append(inscription.individu)

    # Recherche les vaccins existants
    dict_vaccins = {}
    for vaccin in Vaccin.objects.select_related("type_vaccin", "individu").prefetch_related("type_vaccin__types_maladies").filter(individu_id__in=liste_individus):
        dict_vaccins.setdefault(vaccin.individu, [])
        dict_vaccins[vaccin.individu].append(vaccin)

    # Recherche les vaccins manquants
    types_maladies = TypeMaladie.objects.filter(vaccin_obligatoire=True).order_by("nom")
    resultats = {}
    for individu in liste_individus:
        for maladie in types_maladies:
            if not individu.date_naiss or not maladie.vaccin_date_naiss_min or (maladie.vaccin_date_naiss_min and individu.date_naiss >= maladie.vaccin_date_naiss_min):
                valide = False
                for vaccin in dict_vaccins.get(individu, []):
                    if maladie in vaccin.type_vaccin.types_maladies.all():
                        if vaccin.type_vaccin.duree_validite:
                            date_fin_validite = vaccin.date + utils_dates.ConvertDureeStrToDuree(vaccin.type_vaccin.duree_validite)
                            if date_fin_validite >= datetime.date.today():
                                valide = True
                        else:
                            valide = True
                if not valide:
                    resultats.setdefault(individu, [])
                    resultats[individu].append({"label": maladie.nom, "valide": valide})

    return resultats


def Get_tous_vaccins():
    # Recherche les individus
    liste_individus = Individu.objects.all()

    # Recherche les vaccins existants
    dict_vaccins = {}
    for vaccin in Vaccin.objects.select_related("type_vaccin", "individu").prefetch_related("type_vaccin__types_maladies").all():
        dict_vaccins.setdefault(vaccin.individu, [])
        dict_vaccins[vaccin.individu].append(vaccin)

    # Recherche les maladies
    types_maladies = TypeMaladie.objects.all().order_by("nom")
    resultats = {}
    for individu in liste_individus:
        for maladie in types_maladies:
            if maladie.vaccin_obligatoire and (not individu.date_naiss or not maladie.vaccin_date_naiss_min or (maladie.vaccin_date_naiss_min and individu.date_naiss >= maladie.vaccin_date_naiss_min)):
                obligatoire = True
            else:
                obligatoire = False

            valide = False
            dernier_rappel = None
            for vaccin in dict_vaccins.get(individu, []):
                if maladie in vaccin.type_vaccin.types_maladies.all():
                    if not dernier_rappel or vaccin.date > dernier_rappel:
                        dernier_rappel = vaccin.date
                    if vaccin.type_vaccin.duree_validite:
                        date_fin_validite = vaccin.date + utils_dates.ConvertDureeStrToDuree(vaccin.type_vaccin.duree_validite)
                        if date_fin_validite >= datetime.date.today():
                            valide = True
                    else:
                        valide = True

            resultats.setdefault(individu, [])
            resultats[individu].append({"label": maladie.nom, "valide": valide, "dernier_rappel": dernier_rappel, "pk": maladie.pk, "obligatoire": obligatoire})

    return resultats
