# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import TypePieceCollaborateur, PieceCollaborateur, ContratCollaborateur, Collaborateur


def Get_pieces_manquantes(collaborateur=None, date_reference=None, only_invalides=False):
    """ Retourne les pièces manquantes d'un collaborateur """
    if not date_reference:
        date_reference = datetime.date.today()

    # Récupération des types de pièces correspondant aux pièces actuellement valables
    types_pieces_existants = list({piece.type_piece: True for piece in PieceCollaborateur.objects.select_related("type_piece").filter(collaborateur=collaborateur, date_fin__gte=date_reference, type_piece__isnull=False, statut="VALIDE")}.keys())
    types_postes_contrats = list({contrat.type_poste: True for contrat in ContratCollaborateur.objects.select_related("type_poste").filter(Q(collaborateur=collaborateur) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today())))}.keys())
    qualifications_collaborateur = collaborateur.qualifications.all()

    resultats = []
    for type_piece in TypePieceCollaborateur.objects.prefetch_related("qualifications", "postes").all():

        # Recherche si ce type de pièce est à fournir
        necessaire = False
        if type_piece.obligatoire == "OUI":
            necessaire = True
        elif type_piece.obligatoire == "QUALIFICATIONS":
            for qualification in qualifications_collaborateur:
                if qualification in type_piece.qualifications.all():
                    necessaire = True
        elif type_piece.obligatoire == "POSTES":
            for type_poste in types_postes_contrats:
                if type_poste in type_piece.postes.all():
                    necessaire = True

        # Vérifie si le collaborateur a ce type de pièce valide
        valide = type_piece in types_pieces_existants

        if necessaire and (not only_invalides or not valide):
            href = reverse_lazy("collaborateur_pieces_saisie_rapide", kwargs={"idcollaborateur": collaborateur.pk, "idtype_piece": type_piece.pk}) if not valide else None
            resultats.append({"label": type_piece.nom, "valide": valide, "type_piece": type_piece, "titre": "Cliquez ici pour créer immédiatement cette pièce", "href": href})

    return resultats


DATE_ILLIMITEE = datetime.date(2999, 1, 1)
LABELS_ETATS = {"ABSENTE": "non fournie", "EXPIREE": "expirée", "ATTENTE": "transmise, à vérifier", "REFUSEE": "refusée", "BIENTOT": "expire bientôt"}


def Get_liste_pieces_manquantes(collaborateurs=[], date_reference=None, delai_expiration=0):
    """ Pièces manquantes ou bientôt expirées de plusieurs collaborateurs (calcul groupé).
        Renvoie {idcollaborateur: [{"type_piece", "etat", "date_fin", "texte"}]} pour les collaborateurs concernés.
        Etats : ABSENTE (jamais fournie), EXPIREE, ATTENTE (transmise par le collaborateur, à vérifier), REFUSEE, BIENTOT (valide mais expire dans le délai). """
    date_reference = date_reference or datetime.date.today()
    date_alerte = date_reference + datetime.timedelta(days=delai_expiration or 0)
    collaborateurs = list(collaborateurs)
    ids = [collaborateur.pk for collaborateur in collaborateurs]
    types_pieces = list(TypePieceCollaborateur.objects.prefetch_related("qualifications", "postes").order_by("nom"))

    # Qualifications des collaborateurs
    qualifications = {}
    for idcollaborateur, idqualification in Collaborateur.qualifications.through.objects.filter(collaborateur_id__in=ids).values_list("collaborateur_id", "typequalificationcollaborateur_id"):
        qualifications.setdefault(idcollaborateur, set()).add(idqualification)

    # Postes des contrats en cours ou à venir à la date de référence
    postes = {}
    for idcollaborateur, idposte in ContratCollaborateur.objects.filter(Q(collaborateur_id__in=ids) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))).values_list("collaborateur_id", "type_poste_id"):
        postes.setdefault(idcollaborateur, set()).add(idposte)

    # Pièces existantes
    pieces = {}
    for piece in PieceCollaborateur.objects.filter(collaborateur_id__in=ids, type_piece__isnull=False):
        pieces.setdefault((piece.collaborateur_id, piece.type_piece_id), []).append(piece)

    # Conditions de chaque type de pièce
    conditions = {type_piece.pk: {"qualifications": {qualification.pk for qualification in type_piece.qualifications.all()},
                                  "postes": {poste.pk for poste in type_piece.postes.all()}} for type_piece in types_pieces}

    resultats = {}
    for idcollaborateur in ids:
        for type_piece in types_pieces:
            # Le type de pièce est-il exigé pour ce collaborateur ?
            if type_piece.obligatoire == "OUI":
                necessaire = True
            elif type_piece.obligatoire == "QUALIFICATIONS":
                necessaire = bool(conditions[type_piece.pk]["qualifications"] & qualifications.get(idcollaborateur, set()))
            elif type_piece.obligatoire == "POSTES":
                necessaire = bool(conditions[type_piece.pk]["postes"] & postes.get(idcollaborateur, set()))
            else:
                necessaire = False
            if not necessaire:
                continue

            # Recherche de la situation de la pièce
            liste = pieces.get((idcollaborateur, type_piece.pk), [])
            valides = [piece for piece in liste if piece.statut == "VALIDE" and (piece.date_fin or DATE_ILLIMITEE) >= date_reference]
            if valides:
                date_fin = max(piece.date_fin or DATE_ILLIMITEE for piece in valides)
                if not delai_expiration or date_fin == DATE_ILLIMITEE or date_fin > date_alerte:
                    continue
                etat = "BIENTOT"
            elif [piece for piece in liste if piece.statut == "ATTENTE"]:
                etat, date_fin = "ATTENTE", None
            elif [piece for piece in liste if piece.statut == "VALIDE"]:
                etat, date_fin = "EXPIREE", max(piece.date_fin for piece in liste if piece.statut == "VALIDE")
            elif [piece for piece in liste if piece.statut == "REFUSEE"]:
                etat, date_fin = "REFUSEE", None
            else:
                etat, date_fin = "ABSENTE", None

            texte = type_piece.nom
            if etat in ("EXPIREE", "BIENTOT"):
                texte += " (%s le %s)" % ("expirée" if etat == "EXPIREE" else "expire", date_fin.strftime("%d/%m/%Y"))
            elif etat != "ABSENTE":
                texte += " (%s)" % LABELS_ETATS[etat]
            resultats.setdefault(idcollaborateur, []).append({"type_piece": type_piece, "etat": etat, "date_fin": date_fin, "texte": texte})

    return resultats
