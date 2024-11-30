# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy

CATEGORIES = [
    ("saisie_libre", "Saisie libre"),
    ("portail", "Rappel des données du compte internet"),
]

MOTSCLES_STANDARDS = [
    ("{UTILISATEUR_NOM_COMPLET}", "Nom complet de l'utilisateur"),
    ("{UTILISATEUR_NOM}", "Nom de famille de l'utilisateur"),
    ("{UTILISATEUR_PRENOM}", "Prénom de l'utilisateur"),
    ("{DATE_COURTE}", "Date du jour courte"),
    ("{DATE_LONGUE}", "Date du jour longue"),
]

MOTSCLES = {

    "saisie_libre": [],

    "portail": [
        ("{NOM_FAMILLE}", "Nom de la famille"),
        ("{IDENTIFIANT_INTERNET}", "Identifiant du compte internet"),
        ("{MOTDEPASSE_INTERNET}", "Mot de passe du compte internet"),
        ("{DATE_EXPIRATION_MOTDEPASSE}", "Date d'expiration du mot de passe du compte internet"),
    ],

}


def Get_mots_cles(categorie=""):
    listeTemp = copy.deepcopy(MOTSCLES_STANDARDS)
    if categorie in MOTSCLES:
        listeTemp.extend(MOTSCLES[categorie])
    return listeTemp


