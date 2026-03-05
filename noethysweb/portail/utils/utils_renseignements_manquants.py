# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from core.models import Individu, Rattachement


def Get_renseignements_manquants_individu(individu=None):
    """
    Retourne les renseignements manquants pour un individu.

    Args:
        individu: instance Individu

    Returns:
        dict avec :
            - 'nbre' : nombre de champs manquants
            - 'page_cible' : 'identite' ou 'coords' selon le type de manquant
            - 'message_manquant' : texte décrivant les champs manquants
    """
    if not individu:
        return {'nbre': 0, 'page_cible': None, 'message_manquant': ""}

    nbre_manquants = 0
    page_cible = None
    message_manquant = ""
    manquant_identite = False
    manquant_coords = False
    tmp_msg = ""

    # Vérification identité
    if not individu.nom:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- nom\n"
    if not individu.prenom:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- prénom\n"
    if not individu.civilite:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- civilité\n"
    if not individu.date_naiss:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- date de naissance\n"
    if not individu.cp_naiss:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- code postal de naissance\n"
    if not individu.ville_naiss:
        nbre_manquants += 1
        manquant_identite = True
        tmp_msg += "- ville de naissance\n"

    # Vérification coordonnées
    rattachement = Rattachement.objects.filter(individu=individu).first()
    if rattachement and rattachement.categorie == 1:  # Représentant
        if not individu.rue_resid:
            nbre_manquants += 1
            manquant_coords = True
            tmp_msg += "- rue de domicile\n"
        if not individu.cp_resid:
            nbre_manquants += 1
            manquant_coords = True
            tmp_msg += "- code postal de domicile\n"
        if not individu.ville_resid:
            nbre_manquants += 1
            manquant_coords = True
            tmp_msg += "- ville de domicile\n"
        if not individu.tel_mobile and not individu.tel_domicile:
            nbre_manquants += 1
            manquant_coords = True
            tmp_msg += "- numéro de téléphone\n"
        if not individu.mail:
            nbre_manquants += 1
            manquant_coords = True
            tmp_msg += "- adresse mail\n"

    # Détermination de la page à cibler
    if manquant_identite:
        page_cible = 'identite'
    elif manquant_coords:
        page_cible = 'coords'

    if nbre_manquants > 0:
        message_manquant = f"Il manque pour {individu.prenom} {individu.nom} :\n{tmp_msg}\n"

    return {
        'nbre': nbre_manquants,
        'page_cible': page_cible,
        'message_manquant': message_manquant
    }


def Get_renseignements_manquants_par_inscriptions(inscriptions):
    """
    Version optimisée : retourne les renseignements manquants par individu pour une liste d'inscriptions.
    BATCH : 1 requête SQL au total peu importe le nombre d'inscriptions.

    Args:
        inscriptions: QuerySet ou liste d'instances Inscription

    Returns:
        dict[individu.pk] -> dict avec 'nbre', 'page_cible', 'message_manquant'
    """
    inscriptions_list = list(inscriptions)
    
    if not inscriptions_list:
        return {}

    # Extraire tous les individus uniques
    individus = list({ins.individu for ins in inscriptions_list})
    individu_ids = [ind.pk for ind in individus]

    # UNE seule requête pour tous les rattachements
    rattachements_qs = Rattachement.objects.filter(individu__in=individu_ids)
    dict_rattachements = {r.individu_id: r for r in rattachements_qs}

    # Construire les résultats par individu
    dict_resultats = {}
    for individu in individus:
        nbre_manquants = 0
        page_cible = None
        message_manquant = ""
        manquant_identite = False
        manquant_coords = False
        tmp_msg = ""

        # Vérification identité
        if not individu.nom:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- nom\n"
        if not individu.prenom:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- prénom\n"
        if not individu.civilite:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- civilité\n"
        if not individu.date_naiss:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- date de naissance\n"
        if not individu.cp_naiss:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- code postal de naissance\n"
        if not individu.ville_naiss:
            nbre_manquants += 1
            manquant_identite = True
            tmp_msg += "- ville de naissance\n"

        # Vérification coordonnées (utilise le dict pré-chargé)
        rattachement = dict_rattachements.get(individu.pk)
        if rattachement and rattachement.categorie == 1:  # Représentant
            if not individu.rue_resid:
                nbre_manquants += 1
                manquant_coords = True
                tmp_msg += "- rue de domicile\n"
            if not individu.cp_resid:
                nbre_manquants += 1
                manquant_coords = True
                tmp_msg += "- code postal de domicile\n"
            if not individu.ville_resid:
                nbre_manquants += 1
                manquant_coords = True
                tmp_msg += "- ville de domicile\n"
            if not individu.tel_mobile and not individu.tel_domicile:
                nbre_manquants += 1
                manquant_coords = True
                tmp_msg += "- numéro de téléphone\n"
            if not individu.mail:
                nbre_manquants += 1
                manquant_coords = True
                tmp_msg += "- adresse mail\n"

        # Détermination de la page à cibler
        if manquant_identite:
            page_cible = 'identite'
        elif manquant_coords:
            page_cible = 'coords'

        if nbre_manquants > 0:
            message_manquant = f"Il manque pour {individu.prenom} {individu.nom} :\n{tmp_msg}\n"

        dict_resultats[individu.pk] = {
            'nbre': nbre_manquants,
            'page_cible': page_cible,
            'message_manquant': message_manquant
        }

    return dict_resultats


def Get_renseignements_manquants(famille=None):
    """
    Retourne le nombre de renseignements manquants pour une famille et l'ID du premier rattachement concerné.
    Vérifie les champs obligatoires pour chaque membre de la famille.
    Retourne un dictionnaire: {'nbre': nombre, 'premier_rattachement_id': id ou None, 'page_cible': 'identite' ou 'coords', 'message_manquant': message de toutes les alertes}
    """
    if not famille:
        return {'nbre': 0, 'premier_rattachement_id': None, 'page_cible': None, 'message_manquant': ""}

    nbre_manquants = 0
    premier_rattachement_id = None
    page_cible = None
    message_manquant = ""

    # Récupération de tous les individus rattachés à la famille
    rattachements = Rattachement.objects.select_related('individu').filter(famille=famille, individu__deces=False)

    for rattachement in rattachements:
        individu = rattachement.individu
        individu_manquants = 0
        manquant_identite = False
        manquant_coords = False
        tmp_msg = ""

        if not individu.nom:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg += "- nom\n"
        if not individu.prenom:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg = "- prénom\n"

        # Champs obligatoires pour tous (identité)
        if not individu.civilite:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg += "- civilité\n"
        if not individu.date_naiss:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg += "- date de naissance\n"
        if not individu.cp_naiss:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg += "- code postal de naissance\n"
        if not individu.ville_naiss:
            individu_manquants += 1
            manquant_identite = True
            tmp_msg += "- ville de naissance\n"

        # Vérification des coordonnées pour les parents (titulaires et représentants)
        if rattachement.categorie == 1:  # Représentant
            if not individu.rue_resid:
                individu_manquants += 1
                manquant_coords = True
                tmp_msg += "- rue de domicile\n"
            if not individu.cp_resid:
                individu_manquants += 1
                manquant_coords = True
                tmp_msg += "- code postal de domicile\n"
            if not individu.ville_resid:
                individu_manquants += 1
                manquant_coords = True
                tmp_msg += "- ville de domicile\n"
            if not individu.tel_mobile and not individu.tel_domicile:
                individu_manquants += 1
                manquant_coords = True
                tmp_msg += "- numéro de téléphone\n"
            if not individu.mail:
                individu_manquants += 1
                manquant_coords = True
                tmp_msg += "- adresse mail\n"
        else:
            # Pour les enfants, vérifier si au moins un parent a des coordonnées complètes
            parents = Rattachement.objects.filter(
                famille=famille,
                individu__deces=False
            ).filter(Q(titulaire=True) | Q(categorie=1))

            has_parent_with_coords = False
            for parent_ratt in parents:
                parent = parent_ratt.individu
                if (parent.rue_resid and parent.cp_resid and parent.ville_resid and
                    (parent.tel_mobile or parent.tel_domicile) and parent.mail):
                    has_parent_with_coords = True
                    break

            # Si aucun parent n'a de coordonnées complètes et que l'enfant n'en a pas non plus
            if not has_parent_with_coords:
                if not individu.rue_resid:
                    print('manquant rue_resid')
                    individu_manquants += 1
                    manquant_coords = True
                    tmp_msg += "- rue de domicile\n"
                if not individu.cp_resid:
                    print('manquant cp_resid')
                    individu_manquants += 1
                    manquant_coords = True
                    tmp_msg += "- code postal de domicile\n"
                if not individu.ville_resid:
                    print('manquant ville_resid')
                    individu_manquants += 1
                    manquant_coords = True
                    tmp_msg += "- ville de domicile\n"

        # Mémoriser le premier rattachement avec des manquants
        if individu_manquants > 0:
            if premier_rattachement_id is None:
                premier_rattachement_id = rattachement.pk
                # Prioriser l'identité si des champs y sont manquants, sinon coordonnées
                if manquant_identite:
                    page_cible = 'identite'
                elif manquant_coords:
                    page_cible = 'coords'
            nbre_manquants += individu_manquants
        if nbre_manquants > 0:
            message_manquant += f"Il manque pour {individu.prenom} {individu.nom} :\n{tmp_msg}\n"

    return {'nbre': nbre_manquants, 'premier_rattachement_id': premier_rattachement_id, 'page_cible': page_cible, 'message_manquant': message_manquant}
