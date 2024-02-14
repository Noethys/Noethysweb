# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import Famille, Individu, Piece, TypePiece, Inscription, Rattachement
from core.utils import utils_texte


def Get_pieces_manquantes(famille=None, date_reference=None, only_invalides=False, utilisateur=None, exclure_individus=[]):
    """ Retourne les pièces manquantes d'une famille """
    if not date_reference:
        date_reference = datetime.date.today()

    # Conditions SQL
    conditions = Q(famille=famille) & Q(individu__deces=False) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
    if utilisateur:
        conditions &= Q(activite__structure__in=utilisateur.structures.all())

    # Lecture de la db
    inscriptions = Inscription.objects.select_related('activite', 'individu', 'activite__structure').prefetch_related('activite__pieces').filter(conditions).exclude(individu__in=exclure_individus)
    pieces_existantes = Piece.objects.select_related('type_piece').filter(Q(famille=famille) | Q(individu__in=[i.individu_id for i in inscriptions]))

    liste_traitees = []
    liste_resultats = []
    for inscription in inscriptions:
        for type_piece in inscription.activite.pieces.all():

            # Vérifie si la pièce existe
            valide = False
            for piece in pieces_existantes:
                if piece.type_piece_id == type_piece.pk and piece.date_fin >= date_reference:
                    if type_piece.public == "famille":
                        valide = True
                    if type_piece.public == "individu" and piece.individu_id == inscription.individu_id:
                        if type_piece.valide_rattachement == True:
                            valide = True
                        elif piece.famille_id == inscription.famille_id:
                            valide = True

            # Création du lien de création
            if valide:
                href = None
            else:
                href = reverse_lazy("famille_pieces_saisie_rapide", kwargs={'idfamille': inscription.famille_id, 'idtype_piece': type_piece.pk, 'idindividu': inscription.individu_id})

            # Mémorise la pièce à fournir
            dict_temp = {
                "label": type_piece.Get_nom(inscription.individu),
                "valide": valide,
                "type_piece": type_piece,
                "titre": "Cliquez ici pour créer immédiatement cette pièce",
                "href": href,
            }
            if type_piece.public == "famille":
                dict_temp["individu"] = None
                temp = (type_piece, None)
            else:
                dict_temp["individu"] = inscription.individu
                temp = (type_piece, inscription.individu)
            if temp not in liste_traitees and (only_invalides == False or valide == False):
                liste_traitees.append(temp)
                liste_resultats.append(dict_temp)

    return liste_resultats


def Get_liste_pieces_manquantes(date_reference=None, activites=None, presents=None, only_concernes=True, liste_familles=[]):
    """ Retourne les pièces manquantes d'un ensemble de familles inscrites ou présentes """
    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des inscriptions
    conditions = Q()
    if activites:
        conditions &= Q(activite__in=activites)
    if presents:
        conditions &= Q(consommation__date__gte=presents[0], consommation__date__lte=presents[1])
    if liste_familles:
        conditions &= Q(famille__in=liste_familles)
    inscriptions = Inscription.objects.select_related('activite', 'individu', 'famille').prefetch_related('activite__pieces').filter(conditions).distinct()

    # Importation des pièces existantes
    conditions = Q(date_debut__lte=date_reference, date_fin__gte=date_reference)
    pieces_existantes = Piece.objects.select_related('type_piece').filter(conditions)

    dict_pieces = {}
    for piece in pieces_existantes:
        if piece.type_piece:
            if piece.type_piece.public == "famille" and piece.famille_id:
                key = "famille_%d_%d" % (piece.famille_id, piece.type_piece_id)
            elif piece.type_piece.public == "individu" and piece.individu_id:
                key = "individu_%d_%d" % (piece.individu_id, piece.type_piece_id)
            else:
                key = None
            if key:
                dict_pieces.setdefault(key, [])
                dict_pieces[key].append(piece)

    liste_traitees = []
    dict_resultats = {}
    for inscription in inscriptions:
        dict_resultats.setdefault(inscription.famille, [])

        for type_piece in inscription.activite.pieces.all():
            # Vérifie si la pièce existe
            valide = False
            if type_piece.public == "famille":
                key = "famille_%d_%d" % (inscription.famille_id, type_piece.pk)
            else:
                key = "individu_%d_%d" % (inscription.individu_id, type_piece.pk)
            for piece in dict_pieces.get(key, []):
                if type_piece.public == "famille" and piece.famille_id == inscription.famille_id:
                    valide = True
                if type_piece.public == "individu" and piece.individu_id == inscription.individu_id:
                    if type_piece.valide_rattachement == True:
                        valide = True
                    elif piece.famille_id == inscription.famille_id:
                        valide = True

            # Création du lien de création
            if valide:
                href = None
            else:
                href = reverse_lazy("famille_pieces_saisie_rapide", kwargs={'idfamille': inscription.famille_id, 'idtype_piece': type_piece.pk, 'idindividu': inscription.individu_id})

            # Mémorise la pièce à fournir
            dict_temp = {
                "label": type_piece.Get_nom(inscription.individu),
                "valide": valide,
                "type_piece": type_piece,
                "titre": "Cliquez ici pour créer immédiatement cette pièce",
                "href": href,
            }
            if type_piece.public == "famille":
                dict_temp["individu"] = None
                temp = (type_piece, None, inscription.famille_id)
            else:
                dict_temp["individu"] = inscription.individu
                temp = (type_piece, inscription.individu, inscription.famille_id)
            if temp not in liste_traitees and not valide:
                liste_traitees.append(temp)
                dict_resultats[inscription.famille].append(dict_temp)

    # Tri et filtre des résultats
    dict_final = {}
    for famille, liste_pieces in dict_resultats.items():
        if not only_concernes or liste_pieces:
            liste_pieces = sorted(liste_pieces, key=lambda x: x["label"])
            texte = utils_texte.Convert_liste_to_texte_virgules([x["label"] for x in liste_pieces])
            dict_final[famille.pk] = {"texte": texte, "nbre": len(liste_pieces), "liste": liste_pieces, "nom_famille": famille.nom}

    return dict_final


def Get_liste_pieces_necessaires(date_reference=None, activite=None, famille=None, individu=None):
    """ Retourne les pièces nécessaires à l'inscription d'un individu sur une activité donnée pour une famille et un individu donné """
    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des pièces existantes de la famille
    dict_pieces = {}
    for piece in Piece.objects.select_related("type_piece").filter(famille=famille, date_debut__lte=date_reference, date_fin__gte=date_reference):
        if piece.type_piece:
            key = "famille_%d_%d" % (piece.famille_id, piece.type_piece_id) if piece.type_piece.public == "famille" else "individu_%d_%d" % (piece.individu_id, piece.type_piece_id)
            dict_pieces.setdefault(key, [])
            dict_pieces[key].append(piece)

    liste_pieces_necessaires = []
    for type_piece in activite.pieces.all():
        # Vérifie si la pièce existe
        valide = False
        key = "famille_%d_%d" % (famille.pk, type_piece.pk) if type_piece.public == "famille" else "individu_%d_%d" % (individu.pk, type_piece.pk)
        for piece in dict_pieces.get(key, []):
            if type_piece.public == "famille" and piece.famille_id == famille.pk:
                valide = True
            if type_piece.public == "individu" and piece.individu_id == individu.pk:
                if type_piece.valide_rattachement == True:
                    valide = True
                elif piece.famille_id == famille.pk:
                    valide = True

        liste_pieces_necessaires.append({"type_piece": type_piece, "valide": valide, "document": type_piece.type_piece_document.first()})

    return liste_pieces_necessaires
