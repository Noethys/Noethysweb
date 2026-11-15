# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

LISTE_ONGLETS = [
    {"code": "resume", "label": "Résumé", "icone": "fa-home", "url": "collaborateur_resume"},
    {"code": "identite", "label": "Identité", "icone": "fa-user", "url": "collaborateur_identite"},
    {"code": "groupes", "label": "Groupes", "icone": "fa-users", "url": "collaborateur_groupes"},
    {"code": "questionnaire", "label": "Questionnaire", "icone": "fa-question", "url": "collaborateur_questionnaire"},
    {"code": "coords", "label": "Coordonnées", "icone": "fa-map-marker", "url": "collaborateur_coords"},
    {"code": "qualifications", "label": "Qualifications", "icone": "fa-graduation-cap", "url": "collaborateur_qualifications"},
    {"code": "pieces", "label": "Pièces", "icone": "fa-file-text-o", "url": "collaborateur_pieces_liste"},
    {"code": "contrats", "label": "Contrats", "icone": "fa-edit", "url": "collaborateur_contrats_liste"},
    {"code": "evenements", "label": "Evènements", "icone": "fa-calendar", "url": "collaborateur_evenements_liste"},
    {"code": "outils", "label": "Outils", "icone": "fa-wrench", "url": "collaborateur_outils"},
    {"code": "planning", "label": "Planning", "icone": "fa-calendar-o", "url": "collaborateur_planning"},
    {"code": "conges", "label": "Congés", "icone": "fa-plane", "url": "collaborateur_conges"},
    {"code": "espace", "label": "Espace collaborateur", "icone": "fa-globe", "url": "collaborateur_espace"},
]
ONGLETS_SANS_PERMISSION = ("planning", "conges")       # Ces onglets dépendent des permissions du planning et des congés
ONGLETS_SANS_MODIFICATION = ("resume", "outils")


# ------------------------------------------------- Jetons des actions déclenchées par un lien -------------------------------------------------

def Jeton_action(user=None, *valeurs):
    """ Jeton signé, propre à l'utilisateur, à ajouter aux liens qui modifient des données (protection contre la falsification de requêtes) """
    from django.core import signing
    return signing.Signer(salt="collaborateurs.actions").signature(":".join([str(user.pk)] + [str(valeur) for valeur in valeurs]))


def Verifier_jeton(jeton="", user=None, *valeurs):
    import hmac
    return bool(jeton) and hmac.compare_digest(str(jeton), Jeton_action(user, *valeurs))


def Ajouter_jetons_saisie_rapide(pieces=[], user=None, collaborateur=None):
    """ Ajoute le jeton aux liens de saisie rapide des pièces manquantes """
    for piece in pieces:
        if piece.get("href"):
            piece["href"] = "%s?jeton=%s" % (piece["href"], Jeton_action(user, "saisie_rapide", collaborateur.pk, piece["type_piece"].pk))
    return pieces


# ------------------------------------------------- Contrats -------------------------------------------------

def Condition_contrat_en_cours(date=None, prefixe="contratcollaborateur__"):
    """ Condition Q : contrat commencé et non terminé à la date indiquée (aujourd'hui par défaut) """
    import datetime
    from django.db.models import Q
    date = date or datetime.date.today()
    return Q(**{prefixe + "date_debut__lte": date}) & (Q(**{prefixe + "date_fin__isnull": True}) | Q(**{prefixe + "date_fin__gte": date}))


def Situation_contrat(contrats=[], date=None):
    """ Situation d'un collaborateur d'après ses contrats : {"etat": EN_COURS | A_VENIR | TERMINE | AUCUN, "contrat": contrat concerné} """
    import datetime
    date = date or datetime.date.today()
    contrats = sorted(contrats, key=lambda contrat: contrat.date_debut)
    en_cours = [contrat for contrat in contrats if contrat.date_debut <= date and (not contrat.date_fin or contrat.date_fin >= date)]
    if en_cours:
        return {"etat": "EN_COURS", "contrat": en_cours[-1]}
    a_venir = [contrat for contrat in contrats if contrat.date_debut > date]
    if a_venir:
        return {"etat": "A_VENIR", "contrat": a_venir[0]}
    if contrats:
        return {"etat": "TERMINE", "contrat": max(contrats, key=lambda contrat: contrat.date_fin or contrat.date_debut)}
    return {"etat": "AUCUN", "contrat": None}
