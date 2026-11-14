# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Import des valeurs par défaut du paramétrage des collaborateurs.

Les fonctions n'ajoutent que les valeurs absentes (comparaison du nom sans tenir compte des majuscules)
et ne modifient jamais les valeurs existantes. Le paramètre apps permet de les utiliser dans une migration
avec les modèles historiques.
"""

from core.data import data_valeurs_defaut_collaborateurs as DATA


def _Modele(apps, nom):
    if apps:
        return apps.get_model("core", nom)
    from core import models
    return getattr(models, nom)


def _Trouver(modele, nom):
    return modele.objects.filter(nom__iexact=nom).order_by("pk").first()


def Importer_types_contrats(apps=None):
    TypeContrat = _Modele(apps, "TypeContratCollaborateur")
    nbre = 0
    for nom in DATA.TYPES_CONTRATS:
        if not _Trouver(TypeContrat, nom):
            TypeContrat.objects.create(nom=nom)
            nbre += 1
    return {"ajouts": nbre}


def _Creer_categorie(TypeEvenement, valeurs):
    return TypeEvenement.objects.create(nom=valeurs["nom"], type=valeurs["type"], temps_travail_objectif=valeurs["objectif"],
                                        chevauchement_possible=valeurs["chevauchement"], couleur=valeurs["couleur"])


def Importer_categories_evenements(apps=None):
    TypeEvenement = _Modele(apps, "TypeEvenementCollaborateur")
    nbre = 0
    for valeurs in DATA.CATEGORIES_EVENEMENTS:
        if not _Trouver(TypeEvenement, valeurs["nom"]):
            _Creer_categorie(TypeEvenement, valeurs)
            nbre += 1
    return {"ajouts": nbre}


def Importer_types_conges(apps=None):
    TypeConge = _Modele(apps, "TypeCongeCollaborateur")
    TypeEvenement = _Modele(apps, "TypeEvenementCollaborateur")
    categories_defaut = {valeurs["nom"]: valeurs for valeurs in DATA.CATEGORIES_EVENEMENTS}
    nbre, nbre_categories = 0, 0
    for ordre, valeurs in enumerate(DATA.TYPES_CONGES, 1):
        if _Trouver(TypeConge, valeurs["nom"]):
            continue
        # Catégorie d'évènements associée (réutilisée si elle existe déjà)
        categorie = _Trouver(TypeEvenement, valeurs["categorie"])
        if not categorie:
            categorie = _Creer_categorie(TypeEvenement, categories_defaut[valeurs["categorie"]])
            nbre_categories += 1
        TypeConge.objects.create(nom=valeurs["nom"], abrege=valeurs["abrege"], unite=valeurs["unite"], categorie=categorie,
                                 mois_debut=valeurs["mois_debut"], solde_negatif=valeurs["solde_negatif"], actif=True,
                                 ordre=ordre, observations=valeurs["observations"] or None)
        nbre += 1
    return {"ajouts": nbre, "categories": nbre_categories}


def Importer_types_qualifications(apps=None):
    TypeQualification = _Modele(apps, "TypeQualificationCollaborateur")
    nbre = 0
    for nom in DATA.TYPES_QUALIFICATIONS:
        if not _Trouver(TypeQualification, nom):
            TypeQualification.objects.create(nom=nom)
            nbre += 1
    return {"ajouts": nbre}


def Importer_types_pieces(apps=None):
    TypePiece = _Modele(apps, "TypePieceCollaborateur")
    TypeQualification = _Modele(apps, "TypeQualificationCollaborateur")
    nbre, nbre_qualifications = 0, 0
    for valeurs in DATA.TYPES_PIECES:
        if _Trouver(TypePiece, valeurs["nom"]):
            continue
        qualification = None
        if valeurs["qualification"]:
            # Qualification associée (créée si elle n'existe pas)
            qualification = _Trouver(TypeQualification, valeurs["qualification"])
            if not qualification:
                qualification = TypeQualification.objects.create(nom=valeurs["qualification"])
                nbre_qualifications += 1
        piece = TypePiece.objects.create(nom=valeurs["nom"], duree_validite=valeurs["duree_validite"],
                                         obligatoire="QUALIFICATIONS" if qualification else "NON")
        if qualification:
            piece.qualifications.add(qualification)
        nbre += 1
    return {"ajouts": nbre, "qualifications": nbre_qualifications}


# Listes importables : code -> (fonction d'import, page de paramétrage, libellé des valeurs)
LISTES = {
    "types_contrats": (Importer_types_contrats, "types_contrats_collaborateurs_liste", "type de contrat", "types de contrats"),
    "categories_evenements": (Importer_categories_evenements, "types_evenements_collaborateurs_liste", "catégorie d'évènements", "catégories d'évènements"),
    "types_conges": (Importer_types_conges, "types_conges_collaborateurs_liste", "type de congé", "types de congés"),
    "types_qualifications": (Importer_types_qualifications, "types_qualifications_collaborateurs_liste", "type de qualification", "types de qualifications"),
    "types_pieces": (Importer_types_pieces, "types_pieces_collaborateurs_liste", "type de pièce", "types de pièces"),
}


def Remplir_tables_vides(apps=None):
    """ Remplissage initial (migration) : seules les tables vides sont remplies.
    Les types de congés et de pièces dépendent d'autres listes (catégories, qualifications) : pour ne pas
    ajouter de valeurs dans une liste déjà paramétrée par l'utilisateur, ils ne sont remplis que si
    cette liste était elle aussi vide. """
    def Vide(nom):
        return not _Modele(apps, nom).objects.exists()

    vides = {nom: Vide(nom) for nom in ("TypeContratCollaborateur", "TypeEvenementCollaborateur", "TypeCongeCollaborateur",
                                        "TypeQualificationCollaborateur", "TypePieceCollaborateur")}
    if vides["TypeContratCollaborateur"]:
        Importer_types_contrats(apps)
    if vides["TypeEvenementCollaborateur"]:
        Importer_categories_evenements(apps)
        if vides["TypeCongeCollaborateur"]:
            Importer_types_conges(apps)
    if vides["TypeQualificationCollaborateur"]:
        Importer_types_qualifications(apps)
        if vides["TypePieceCollaborateur"]:
            Importer_types_pieces(apps)
