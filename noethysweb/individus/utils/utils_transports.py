# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


CATEGORIES = {
    "marche": {
        "label": "Marche",
    },
    "velo": {
        "label": "Vélo",
    },
    "voiture": {
        "label": ("Voiture"),
    },
    "bus": {
        "label": "Bus",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie de bus", "label_pluriel": "compagnies de bus"},
            "lignes": {"label_singulier": "ligne de bus", "label_pluriel": "lignes de bus"},
            "arrets": {"label_singulier": "arrêt de bus", "label_pluriel": "arrêts de bus"},
        },
    },
    "car": {
        "label": "Car",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie de cars", "label_pluriel": "compagnies de cars"},
            "lignes": {"label_singulier": "ligne de cars", "label_pluriel": "lignes de cars"},
            "arrets": {"label_singulier": "arrêt de cars", "label_pluriel": "arrêts de cars"},
        },
    },
    "navette": {
        "label": "Navette",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie de navettes", "label_pluriel": "compagnies de navettes"},
            "lignes": {"label_singulier": "ligne de navettes", "label_pluriel": "lignes de navettes"},
            "arrets": {"label_singulier": "arrêt de navettes", "label_pluriel": "arrêts de navettes"},
        },
    },
    "taxi": {
        "label": "Taxi",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie de taxis", "label_pluriel": "compagnies de taxis"},
        },
    },
    "avion": {
        "label": "Avion",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie aérienne", "label_pluriel": "compagnies aériennes"},
            "lieux": {"label_singulier": "aéroport", "label_pluriel": "aéroports"},
        },
    },
    "bateau": {
        "label": "Bateau",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie maritime", "label_pluriel": "compagnies maritimes"},
            "lieux": {"label_singulier": "port", "label_pluriel": "ports"},
        },
    },
    "train": {
        "label": "Train",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie ferroviaire", "label_pluriel": "compagnies ferroviaires"},
            "lieux": {"label_singulier": "gare", "label_pluriel": "gares"},
        },
    },
    "metro": {
        "label": "Métro",
        "parametrage": {
            "compagnies": {"label_singulier": "compagnie de métro", "label_pluriel": "compagnies de métro"},
            "lignes": {"label_singulier": "ligne de métro", "label_pluriel": "lignes de métro"},
            "arrets": {"label_singulier": "arrêt de métro", "label_pluriel": "arrêts de métro"},
        },
    },
    "pedibus": {
        "label": "Pédibus",
        "parametrage": {
            "lignes": {"label_singulier": "ligne de pédibus", "label_pluriel": "lignes de pédibus"},
            "arrets": {"label_singulier": "arrêt de pédibus", "label_pluriel": "arrêts de pédibus"},
        },
    },
}


def Get_liste_choix_categories():
    return [(code, dict_temp["label"]) for code, dict_temp in CATEGORIES.items()]
