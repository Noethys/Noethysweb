# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import TypePieceCollaborateur, PieceCollaborateur, ContratCollaborateur


def Get_pieces_manquantes(collaborateur=None, date_reference=None, only_invalides=False):
    """ Retourne les pièces manquantes d'un collaborateur """
    if not date_reference:
        date_reference = datetime.date.today()

    # Récupération des types de pièces correspondant aux pièces actuellement valables
    types_pieces_existants = list({piece.type_piece: True for piece in PieceCollaborateur.objects.select_related("type_piece").filter(collaborateur=collaborateur, date_fin__gte=date_reference, type_piece__isnull=False)}.keys())
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
