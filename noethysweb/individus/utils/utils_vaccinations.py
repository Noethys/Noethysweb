# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Count, Q
from core.models import TypeMaladie, TypeVaccin, Vaccin, Individu
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


def Importation_vaccins():
    """ Importe les vaccins et maladies par défaut """
    # Suppression des types de maladies non utilisés
    for type_maladie in TypeMaladie.objects.all().annotate(nbre_individus=Count('individu_maladies')).annotate(nbre_vaccins=Count('vaccin_maladies')):
        if type_maladie.nbre_individus == 0 and type_maladie.nbre_vaccins == 0:
            type_maladie.delete()

    # Création des types de maladies manquants
    types_maladies_defaut = [
        {"nom": "Coqueluche", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Diphtérie", "vaccin_obligatoire": True, "vaccin_date_naiss_min": None},
        {"nom": "Haemophilus influenzae B", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Hépatite B", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Méningocoque C", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Oreillons", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Pneumocoque", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Poliomyélite", "vaccin_obligatoire": True, "vaccin_date_naiss_min": None},
        {"nom": "Rougeole", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Rubéole", "vaccin_obligatoire": True, "vaccin_date_naiss_min": datetime.date(2018, 1, 1)},
        {"nom": "Tétanos", "vaccin_obligatoire": True, "vaccin_date_naiss_min": None},
        {"nom": "Tuberculose", "vaccin_obligatoire": False, "vaccin_date_naiss_min": None},
        {"nom": "Varicelle", "vaccin_obligatoire": False, "vaccin_date_naiss_min": None},
        {"nom": "Otite", "vaccin_obligatoire": False, "vaccin_date_naiss_min": None},
        {"nom": "Roseole", "vaccin_obligatoire": False, "vaccin_date_naiss_min": None},
        {"nom": "Scarlatine", "vaccin_obligatoire": False, "vaccin_date_naiss_min": None},
    ]
    types_maladies_existants = {type_maladie.nom: type_maladie for type_maladie in TypeMaladie.objects.all()}
    for type_maladie_defaut in types_maladies_defaut:
        if type_maladie_defaut["nom"] in types_maladies_existants:
            type_maladie = types_maladies_existants[type_maladie_defaut["nom"]]
            type_maladie.vaccin_obligatoire = type_maladie_defaut["vaccin_obligatoire"]
            type_maladie.vaccin_date_naiss_min = type_maladie_defaut["vaccin_date_naiss_min"]
            type_maladie.save()
        else:
            TypeMaladie.objects.create(**type_maladie_defaut)

    # Supprime les types de vaccins non utilisés
    for type_vaccin in TypeVaccin.objects.all().annotate(nbre_vaccins=Count("vaccin")):
        if type_vaccin.nbre_vaccins == 0:
            type_vaccin.delete()

    # Création des types de vaccins manquants
    types_vaccins_defaut = [
        {"nom": "Coqueluche", "duree_validite": None, "types_maladies": ["Coqueluche",]},
        {"nom": "Diphtérie", "duree_validite": None, "types_maladies": ["Diphtérie",]},
        {"nom": "DTP (Diphtérie, Tétanos et Poliomyélite)", "duree_validite": None, "types_maladies": ["Diphtérie", "Poliomyélite", "Tétanos"]},
        {"nom": "Grippe", "duree_validite": None, "types_maladies": []},
        {"nom": "Haemophilus influenzae B", "duree_validite": None, "types_maladies": ["Haemophilus influenzae B",]},
        {"nom": "Hépatite B", "duree_validite": None, "types_maladies": ["Hépatite B",]},
        {"nom": "Méningocoque C", "duree_validite": None, "types_maladies": ["Méningocoque C",]},
        {"nom": "Oreillons", "duree_validite": None, "types_maladies": ["Oreillons",]},
        {"nom": "Pneumocoque", "duree_validite": None, "types_maladies": ["Pneumocoque",]},
        {"nom": "Poliomyélite", "duree_validite": None, "types_maladies": ["Poliomyélite",]},
        {"nom": "ROR (Rougeole, Oreillons, Rubéole)", "duree_validite": None, "types_maladies": ["Oreillons", "Rougeole" , "Rubéole"]},
        {"nom": "Rougeole", "duree_validite": None, "types_maladies": ["Rougeole",]},
        {"nom": "Rubéole", "duree_validite": None, "types_maladies": ["Rubéole",]},
        {"nom": "Tétanos", "duree_validite": None, "types_maladies": ["Tétanos",]},
        {"nom": "Tuberculose (BCG)", "duree_validite": None, "types_maladies": ["Tuberculose",]},
        {"nom": "Varicelle", "duree_validite": None, "types_maladies": []},
    ]
    types_vaccins_existants = {type_vaccin.nom: type_vaccin for type_vaccin in TypeVaccin.objects.all()}
    types_maladies_existants = {type_maladie.nom: type_maladie for type_maladie in TypeMaladie.objects.all()}
    for type_vaccin_defaut in types_vaccins_defaut:
        if type_vaccin_defaut["nom"] in types_vaccins_existants:
            type_vaccin = types_vaccins_existants[type_vaccin_defaut["nom"]]
            type_vaccin.duree_validite = type_vaccin_defaut["duree_validite"]
            type_vaccin.save()
        else:
            type_vaccin = TypeVaccin.objects.create(nom=type_vaccin_defaut["nom"], duree_validite=type_vaccin_defaut["duree_validite"])
        for nom_type_maladie in type_vaccin_defaut["types_maladies"]:
            if nom_type_maladie in types_maladies_existants:
                type_maladie = types_maladies_existants[nom_type_maladie]
                if type_maladie not in type_vaccin.types_maladies.all():
                    type_vaccin.types_maladies.add(type_maladie)
