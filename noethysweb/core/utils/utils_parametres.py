# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Parametre
import json


def Get(nom=None, categorie=None, utilisateur=None, valeur=None):
    objet, created = Parametre.objects.get_or_create(nom=nom, categorie=categorie, utilisateur=utilisateur, defaults={"parametre": To_db(valeur)})
    return To_python(objet.parametre, valeur)

def Set(nom=None, categorie=None, utilisateur=None, valeur=None):
    objet, created = Parametre.objects.update_or_create(nom=nom, categorie=categorie, utilisateur=utilisateur, defaults={"parametre": To_db(valeur)})

def Get_categorie(categorie=None, utilisateur=None, parametres={}):
    dict_parametres = {}
    liste_ajouts = []
    try:
        parametres_existants = {parametre.nom: parametre for parametre in Parametre.objects.filter(categorie=categorie, utilisateur=utilisateur)}
        for nom, valeur in parametres.items():
            if nom in parametres_existants:
                # Si le paramètre est déjà dans la DB, on le récupère
                dict_parametres[nom] = To_python(parametres_existants[nom].parametre, valeur)
            else:
                # Sinon, on l'enregistre dans la DB
                liste_ajouts.append(Parametre(nom=nom, categorie=categorie, utilisateur=utilisateur, parametre=To_db(valeur)))
                dict_parametres[nom] = valeur

        # Enregistrement des ajouts dans la DB
        if liste_ajouts:
            Parametre.objects.bulk_create(liste_ajouts)
    except:
        parametres_existants = {}
    return dict_parametres

def Set_categorie(categorie=None, utilisateur=None, parametres={}):
    parametres_existants = {parametre.nom: parametre for parametre in Parametre.objects.filter(categorie=categorie, utilisateur=utilisateur)}
    liste_ajouts, liste_modifications = [], []
    for nom, valeur in parametres.items():
        if nom not in parametres_existants:
            liste_ajouts.append(Parametre(nom=nom, categorie=categorie, utilisateur=utilisateur, parametre=To_db(valeur)))
        else:
            parametre = parametres_existants[nom]
            if parametre.parametre != valeur:
                parametre.parametre = To_db(valeur)
                liste_modifications.append(parametre)
    if liste_ajouts:
        Parametre.objects.bulk_create(liste_ajouts)
    if liste_modifications:
        Parametre.objects.bulk_update(liste_modifications, ["parametre"])

    # Ancienne version :
    # for nom, valeur in parametres.items():
    #     objet, created = Parametre.objects.update_or_create(nom=nom, categorie=categorie, utilisateur=utilisateur, defaults={"parametre": To_db(valeur)})

def To_python(valeur=None, defaut=None):
    if not valeur: return valeur
    type_parametre = type(defaut)
    if type_parametre in (tuple, dict, list):
        return json.loads(valeur)
    if type_parametre == int:
        return int(valeur)
    if type_parametre == float:
        return float(valeur)
    if type_parametre == bool:
        return True if valeur == "True" else False
    return valeur

def To_db(valeur=None):
    if not valeur: return valeur
    type_parametre = type(valeur)
    if type_parametre in (tuple, dict, list):
        return json.dumps(valeur)
    return str(valeur)
