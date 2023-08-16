# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy


CATEGORIES = [
    ("contrat_collaborateur", "Contrat collaborateur"),
]

MOTSCLES_STANDARDS = [
    ("{UTILISATEUR_NOM_COMPLET}", "Nom complet de l'utilisateur"),
    ("{UTILISATEUR_NOM}", "Nom de famille de l'utilisateur"),
    ("{UTILISATEUR_PRENOM}", "Prénom de l'utilisateur"),
    ("{UTILISATEUR_SIGNATURE}", "Signature de l'utilisateur"),
    ("{DATE_COURTE}", "Date du jour courte"),
    ("{DATE_LONGUE}", "Date du jour longue"),
    ("{ORGANISATEUR_NOM}", "Nom de l'organisateur"),
    ("{ORGANISATEUR_RUE}", "Rue de l'organisateur"),
    ("{ORGANISATEUR_CP}", "CP de l'organisateur"),
    ("{ORGANISATEUR_VILLE}", "Ville de l'organisateur"),
    ("{ORGANISATEUR_TEL}", "Téléphone de l'organisateur"),
    ("{ORGANISATEUR_MAIL}", "Email de l'organisateur"),
    ("{ORGANISATEUR_SITE}", "Site internet de l'organisateur"),
]

MOTSCLES = {

    "contrat_collaborateur": [
        ("{CONTRAT_ID}", "ID du contrat"),
        ("{CONTRAT_DATE_DEBUT}", "Date de début du contrat"),
        ("{CONTRAT_DATE_FIN}", "Date de fin du contrat"),
        ("{CONTRAT_TYPE_POSTE}", "Type de poste du contrat"),
        ("{CONTRAT_OBSERVATIONS}", "Observations du contrat"),
        ("{COLLABORATEUR_ID}", "ID du collaborateur"),
        ("{COLLABORATEUR_CIVILITE}", "Civilité du collaborateur"),
        ("{COLLABORATEUR_NOM}", "Nom de famille du collaborateur"),
        ("{COLLABORATEUR_NOM_JFILLE}", "Nom de jeune fille du collaborateur"),
        ("{COLLABORATEUR_PRENOM}", "Prénom du collaborateur"),
        ("{COLLABORATEUR_RUE}", "Rue du collaborateur"),
        ("{COLLABORATEUR_CODE_POSTAL}", "Code postal du collaborateur"),
        ("{COLLABORATEUR_VILLE}", "Ville du collaborateur"),
        ("{COLLABORATEUR_TEL_PRO}", "Tél pro du collaborateur"),
        ("{COLLABORATEUR_MAIL_PRO}", "Mail pro du collaborateur"),
        ("{COLLABORATEUR_TEL_DOMICILE}", "Tél domicile du collaborateur"),
        ("{COLLABORATEUR_TEL_PORTABLE}", "Tél portable du collaborateur"),
        ("{COLLABORATEUR_MAIL}", "Email du collaborateur"),
        ("{COLLABORATEUR_MEMO}", "Mémo du collaborateur"),
    ],

}


def Get_mots_cles(categorie=""):
    # Mots-clés standard
    listeTemp = copy.deepcopy(MOTSCLES_STANDARDS)

    # Mots-clés spécifiques à la catégorie
    if categorie in MOTSCLES:
        listeTemp.extend(MOTSCLES[categorie])

    # Mots-clés des questionnaires
    from core.models import QuestionnaireQuestion
    for question in QuestionnaireQuestion.objects.filter(categorie=categorie, visible=True).order_by("ordre"):
        listeTemp.append(("{QUESTION_%d}" % question.pk, question.label))

    return listeTemp
