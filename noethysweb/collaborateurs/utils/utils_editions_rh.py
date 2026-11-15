# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Editions réglementaires : registre unique du personnel, état des qualifications """

import datetime
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Table, Spacer
from core.models import ContratCollaborateur, PieceCollaborateur, TypePieceCollaborateur
from core.utils import utils_dates
from collaborateurs.utils.utils_editions import Impression_edition, Style, P, Date, Style_tableau, COULEUR_TEXTE_CLAIR

PAYSAGE = landscape(A4)
DATE_ILLIMITEE = datetime.date(2999, 1, 1)
DUREE_TEMPS_PLEIN = 35


# ------------------------------------------------- Registre unique du personnel -------------------------------------------------

def Donnees_registre(collaborateurs=[], parametres={}):
    """ Une ligne par contrat, dans l'ordre des embauches. Le numéro d'ordre est calculé sur l'ensemble des contrats de la base. """
    numeros = {idcontrat: numero for numero, idcontrat in enumerate(ContratCollaborateur.objects.order_by("date_debut", "pk").values_list("pk", flat=True), 1)}
    contrats = ContratCollaborateur.objects.select_related("collaborateur", "type_contrat", "type_poste").filter(collaborateur__in=collaborateurs).order_by("date_debut", "pk")
    if parametres.get("periode"):
        debut, fin = [utils_dates.ConvertDateENGtoDate(valeur) for valeur in parametres["periode"].split(";")]
        contrats = [contrat for contrat in contrats if contrat.date_debut <= fin and (not contrat.date_fin or contrat.date_fin >= debut)]
    entetes = ["N°", "Nom", "Nom de naissance", "Prénom", "Sexe", "Date de naissance", "Nationalité", "Emploi", "Qualifications", "Type de contrat", "Date d'entrée", "Date de sortie"]
    lignes = []
    for contrat in contrats:
        collaborateur = contrat.collaborateur
        type_contrat = contrat.type_contrat.nom if contrat.type_contrat else ""
        if parametres.get("afficher_heures") and contrat.heures_hebdo and float(contrat.heures_hebdo) < DUREE_TEMPS_PLEIN:
            type_contrat = ("%s - temps partiel %s h" % (type_contrat, ("%g" % float(contrat.heures_hebdo)).replace(".", ","))).strip(" -")
        lignes.append([numeros.get(contrat.pk), collaborateur.nom, collaborateur.nom_jfille or "", collaborateur.prenom or "", "F" if collaborateur.civilite == "MME" else "M",
                       collaborateur.date_naiss, collaborateur.nationalite or "", contrat.type_poste.nom,
                       ", ".join(qualification.nom for qualification in collaborateur.qualifications.all()), type_contrat, contrat.date_debut, contrat.date_fin])
    return entetes, lignes


class Impression_registre(Impression_edition):

    def Draw(self):
        parametres = self.dict_donnees["parametres"]
        entetes, lignes = Donnees_registre(self.dict_donnees["collaborateurs"], parametres)
        sous_titre = "Registre complet"
        if parametres.get("periode"):
            debut, fin = [utils_dates.ConvertDateENGtoDate(valeur) for valeur in parametres["periode"].split(";")]
            sous_titre = "Contrats en cours entre le %s et le %s" % (Date(debut), Date(fin))
        self.Entete(self.titre, "%s - %d ligne%s" % (sous_titre, len(lignes), "s" if len(lignes) > 1 else ""))
        style = Style("registre", 7.5)
        style_entete = Style("registre_entete", 7.5, gras=True)
        donnees = [[P(entete, style_entete) for entete in entetes]]
        manquants = 0
        for ligne in lignes:
            if not ligne[5] or not ligne[6]:
                manquants += 1
            donnees.append([P(Date(valeur) if isinstance(valeur, datetime.date) else valeur, style) for valeur in ligne])
        parts = (0.04, 0.1, 0.09, 0.09, 0.04, 0.08, 0.08, 0.12, 0.12, 0.1, 0.07, 0.07)
        tableau = Table(donnees, [self.largeur_utile * part for part in parts], repeatRows=1)
        tableau.setStyle(Style_tableau(nbre_lignes=len(donnees), taille=7.5))
        self.story.append(tableau)
        if manquants:
            self.story.append(Spacer(0, 3 * mm))
            self.story.append(P("%d ligne%s sans date de naissance ou sans nationalité : complétez la rubrique Identité des fiches concernées." % (manquants, "s" if manquants > 1 else ""),
                                Style("remarque", 8, couleur=colors.HexColor("#A8323E"))))
        self.story.append(Spacer(0, 3 * mm))
        self.story.append(P("Le registre unique du personnel doit être conservé 5 ans à compter du départ du salarié. Pour les salariés étrangers soumis à autorisation de travail, "
                            "le type et le numéro du titre valant autorisation de travail doivent également y figurer.", Style("mention", 7, couleur=COULEUR_TEXTE_CLAIR)))


# ------------------------------------------------- Etat des qualifications -------------------------------------------------

def Calculer_qualifications(collaborateurs=[], parametres={}):
    """ Pour chaque collaborateur et qualification : {"qualifie", "etat" (VALIDE, EXPIREE, MANQUANTE, SANS_PIECE), "date_fin"} """
    date_reference = parametres["date"]
    qualifications = list(parametres["qualifications"])
    types_pieces = {}
    for type_piece in TypePieceCollaborateur.objects.prefetch_related("qualifications").all():
        for qualification in type_piece.qualifications.all():
            types_pieces.setdefault(qualification.pk, set()).add(type_piece.pk)
    pieces = {}
    for piece in PieceCollaborateur.objects.filter(collaborateur__in=collaborateurs, statut="VALIDE", type_piece__isnull=False):
        pieces.setdefault((piece.collaborateur_id, piece.type_piece_id), []).append(piece)

    resultats = {}
    for collaborateur in collaborateurs:
        ids_qualifications = {qualification.pk for qualification in collaborateur.qualifications.all()}
        for qualification in qualifications:
            if qualification.pk not in ids_qualifications:
                continue
            types = types_pieces.get(qualification.pk, set())
            if not types:
                resultats[(collaborateur.pk, qualification.pk)] = {"etat": "SANS_PIECE", "date_fin": None}
                continue
            liste = [piece for type_piece in types for piece in pieces.get((collaborateur.pk, type_piece), [])]
            valides = [piece for piece in liste if (piece.date_fin or DATE_ILLIMITEE) >= date_reference]
            if valides:
                resultats[(collaborateur.pk, qualification.pk)] = {"etat": "VALIDE", "date_fin": max(piece.date_fin or DATE_ILLIMITEE for piece in valides)}
            elif liste:
                resultats[(collaborateur.pk, qualification.pk)] = {"etat": "EXPIREE", "date_fin": max(piece.date_fin for piece in liste)}
            else:
                resultats[(collaborateur.pk, qualification.pk)] = {"etat": "MANQUANTE", "date_fin": None}
    return qualifications, resultats


def Texte_qualification(resultat=None, afficher_dates=True, court=False):
    if not resultat:
        return ""
    etat, date_fin = resultat["etat"], resultat["date_fin"]
    format_date = (lambda date: date.strftime("%d/%m/%y")) if court else Date
    if etat == "VALIDE":
        if afficher_dates and date_fin and date_fin < DATE_ILLIMITEE:
            return "Oui\njusqu'au %s" % format_date(date_fin) if court else "Oui, jusqu'au %s" % Date(date_fin)
        return "Oui"
    if etat == "EXPIREE":
        return ("Expirée\nle %s" % format_date(date_fin) if court else "Pièce expirée le %s" % Date(date_fin)) if afficher_dates else "Pièce expirée"
    if etat == "MANQUANTE":
        return "Pièce\nà fournir" if court else "Pièce à fournir"
    return "Oui"


def Donnees_qualifications_xlsx(collaborateurs=[], parametres={}):
    from collaborateurs.utils.utils_editions import Get_contrats, Get_situation
    qualifications, resultats = Calculer_qualifications(collaborateurs, parametres)
    contrats = Get_contrats(collaborateurs)
    entetes = ["Nom", "Prénom", "Poste"] + [qualification.nom for qualification in qualifications]
    lignes = []
    for collaborateur in collaborateurs:
        contrat = Get_situation(contrats.get(collaborateur.pk, []), parametres["date"])
        lignes.append([collaborateur.nom, collaborateur.prenom or "", contrat.type_poste.nom if contrat else ""] +
                      [Texte_qualification(resultats.get((collaborateur.pk, qualification.pk)), parametres.get("afficher_dates")) for qualification in qualifications])
    return entetes, lignes


class Impression_qualifications(Impression_edition):

    def Draw(self):
        from collaborateurs.utils.utils_editions import Get_contrats, Get_situation
        parametres = self.dict_donnees["parametres"]
        collaborateurs = self.dict_donnees["collaborateurs"]
        qualifications, resultats = Calculer_qualifications(collaborateurs, parametres)
        contrats = Get_contrats(collaborateurs)
        self.Entete(self.titre, "Situation au %s - %d collaborateur%s" % (Date(parametres["date"]), len(collaborateurs), "s" if len(collaborateurs) > 1 else ""))
        if not qualifications:
            return

        taille = 7.5 if len(qualifications) <= 6 else 6.5
        style = Style("qualif", taille)
        style_entete = Style("qualif_entete", taille, gras=True, alignement="centre")
        couleurs = {"VALIDE": colors.HexColor("#E6F4EA"), "SANS_PIECE": colors.HexColor("#E6F4EA"), "EXPIREE": colors.HexColor("#FDECEE"), "MANQUANTE": colors.HexColor("#FFF4DB")}
        donnees = [[P("Collaborateur", Style("qualif_entete_g", taille, gras=True)), P("Poste", Style("qualif_entete_g2", taille, gras=True))] +
                   [P(qualification.nom, style_entete) for qualification in qualifications]]
        regles = []
        totaux = {qualification.pk: {"qualifies": 0, "valides": 0} for qualification in qualifications}
        for num_ligne, collaborateur in enumerate(collaborateurs, 1):
            contrat = Get_situation(contrats.get(collaborateur.pk, []), parametres["date"])
            ligne = [P(collaborateur.Get_nom(), Style("qualif_nom", taille, gras=True)), P(contrat.type_poste.nom if contrat else "", style)]
            for num_colonne, qualification in enumerate(qualifications, 2):
                resultat = resultats.get((collaborateur.pk, qualification.pk))
                ligne.append(P(Texte_qualification(resultat, parametres.get("afficher_dates"), court=True), Style("qualif_cellule", taille, alignement="centre")))
                if resultat:
                    totaux[qualification.pk]["qualifies"] += 1
                    if resultat["etat"] in ("VALIDE", "SANS_PIECE"):
                        totaux[qualification.pk]["valides"] += 1
                    regles.append(("BACKGROUND", (num_colonne, num_ligne), (num_colonne, num_ligne), couleurs[resultat["etat"]]))
            donnees.append(ligne)

        # Totaux par qualification
        nbre = len(collaborateurs)
        ligne_total = [P("Collaborateurs qualifiés (sur %d)" % nbre, Style("qualif_total", taille, gras=True)), ""]
        for qualification in qualifications:
            total = totaux[qualification.pk]
            texte = "%d (%d %%)" % (total["qualifies"], round(100.0 * total["qualifies"] / nbre) if nbre else 0)
            if total["valides"] != total["qualifies"]:
                texte += "\ndont %d justifié%s" % (total["valides"], "s" if total["valides"] > 1 else "")
            ligne_total.append(P(texte, Style("qualif_total_c", taille, gras=True, alignement="centre")))
        donnees.append(ligne_total)

        largeur_nom, largeur_poste = 42 * mm, 34 * mm
        largeur_qualif = (self.largeur_utile - largeur_nom - largeur_poste) / len(qualifications)
        tableau = Table(donnees, [largeur_nom, largeur_poste] + [largeur_qualif] * len(qualifications), repeatRows=1)
        style_tableau = Style_tableau(nbre_lignes=0, taille=taille)
        for regle in regles:
            style_tableau.add(*regle)
        style_tableau.add("BACKGROUND", (0, len(donnees) - 1), (-1, len(donnees) - 1), colors.HexColor("#EEF1F5"))
        style_tableau.add("LINEABOVE", (0, len(donnees) - 1), (-1, len(donnees) - 1), 1, colors.HexColor("#ADB5BD"))
        style_tableau.add("SPAN", (0, len(donnees) - 1), (1, len(donnees) - 1))
        tableau.setStyle(style_tableau)
        self.story.append(tableau)
        self.story.append(Spacer(0, 3 * mm))
        legende = Table([["", P("Qualifié, pièce valable", style), "", P("Qualifié, pièce à fournir", style), "", P("Qualifié, pièce expirée", style)]],
                        [5 * mm, 40 * mm, 5 * mm, 40 * mm, 5 * mm, 40 * mm], hAlign="LEFT")
        style_legende = Style_tableau(entete=False, zebra=False, taille=taille)
        style_legende = [("BACKGROUND", (0, 0), (0, 0), couleurs["VALIDE"]), ("BACKGROUND", (2, 0), (2, 0), couleurs["MANQUANTE"]), ("BACKGROUND", (4, 0), (4, 0), couleurs["EXPIREE"]),
                         ("BOX", (0, 0), (0, 0), 0.25, colors.HexColor("#C9D1DA")), ("BOX", (2, 0), (2, 0), 0.25, colors.HexColor("#C9D1DA")), ("BOX", (4, 0), (4, 0), 0.25, colors.HexColor("#C9D1DA"))]
        from reportlab.platypus import TableStyle
        legende.setStyle(TableStyle(style_legende))
        self.story.append(legende)
