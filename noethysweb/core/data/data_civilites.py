# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

LISTE_CIVILITES = (
    (u"ADULTE",
        (
            {"id": 1, "label": "Monsieur", "abrege": "M.", "image": "homme.png", "sexe": "M"},
            {"id": 2, "label": "Mademoiselle", "abrege": "Melle", "image": "femme.png", "sexe": "F"},
            {"id": 3, "label": "Madame", "abrege": "Mme", "image": "femme.png", "sexe": "F"},
        )),
    (u"ENFANT",
        (
            {"id": 4, "label": "Garçon", "abrege": None, "image": "garcon.png", "sexe": "M"},
            {"id": 5, "label": "Fille", "abrege": None, "image": "fille.png", "sexe": "F"},
        )),
    (u"AUTRE",
        (
            {"id": 6, "label": "Collectivité", "abrege": None, "image": "organisme.png", "sexe": None},
            {"id": 7, "label": "Association", "abrege": None,  "image": "organisme.png", "sexe": None},
            {"id": 8, "label": "Organisme", "abrege": None, "image": "organisme.png", "sexe": None},
            {"id": 9, "label": "Entreprise", "abrege": None, "image": "organisme.png", "sexe": None},
        )),
    )


def GetListeCivilitesForModels():
    liste_civilites = []
    for categorie, items in LISTE_CIVILITES:
        for dict_civilite in items:
            liste_civilites.append((dict_civilite["id"], dict_civilite["label"]))
    return liste_civilites

def GetCiviliteForIndividu(individu=None):
    for categorie, items in LISTE_CIVILITES:
        for dict_civilite in items:
            if dict_civilite["id"] == individu.civilite:
                dict_civilite["categorie"] = categorie
                return dict_civilite
    return None

def GetDictCivilites():
    dict_civilites = {}
    for categorie, items in LISTE_CIVILITES:
        for dict_civilite in items:
            dict_civilites[dict_civilite["id"]] = dict_civilite
    return dict_civilites

def Get_abrege(individu=None):
    try:
        return GetCiviliteForIndividu(individu)["abrege"]
    except:
        return ""