# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Outils communs aux éditions du module Collaborateurs (sélection des collaborateurs, styles et éléments des PDF) """

import datetime, os
from django.conf import settings
from django.db.models import Q, Exists, OuterRef
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Image
from core.models import ContratCollaborateur, Organisateur
from core.utils import utils_polices
from core.utils.utils_impression import Impression
from collaborateurs.utils.utils_collaborateur import Condition_contrat_en_cours, Situation_contrat

FONT, FONT_BOLD = utils_polices.FONT_NORMAL, utils_polices.FONT_BOLD
COULEUR_ENTETE = colors.HexColor("#EEF1F5")
COULEUR_TRAIT = colors.HexColor("#C9D1DA")
COULEUR_TEXTE_CLAIR = colors.HexColor("#6C757D")
COULEUR_PRINCIPALE = colors.HexColor("#3C8DBC")
JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


# ------------------------------------------------- Sélection des collaborateurs -------------------------------------------------

def Get_collaborateurs(user=None, situation="en_poste", groupes=None, date_reference=None, ids=None):
    """ Collaborateurs accessibles à l'utilisateur, filtrés par situation et par groupes """
    from collaborateurs.views.planning_individuel import Collaborateurs_accessibles
    date_reference = date_reference or datetime.date.today()
    collaborateurs = Collaborateurs_accessibles(user)
    if groupes:
        collaborateurs = collaborateurs.filter(groupes__in=groupes)
    if situation == "en_poste":
        collaborateurs = collaborateurs.filter(Exists(ContratCollaborateur.objects.filter(Condition_contrat_en_cours(date=date_reference, prefixe=""), collaborateur=OuterRef("pk"))))
    elif situation == "a_venir":
        collaborateurs = collaborateurs.filter(Exists(ContratCollaborateur.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference), collaborateur=OuterRef("pk"))))
    if ids is not None:
        collaborateurs = collaborateurs.filter(pk__in=ids)
    return list(collaborateurs.distinct().prefetch_related("groupes", "qualifications").order_by("nom", "prenom"))


def Get_contrats(collaborateurs=[]):
    """ {idcollaborateur: [contrats triés par date]} """
    contrats = {}
    for contrat in ContratCollaborateur.objects.select_related("type_contrat", "type_poste").filter(collaborateur__in=collaborateurs).order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
    return contrats


def Get_situation(contrats=[], date=None):
    """ Contrat de référence (en cours, sinon à venir, sinon le dernier) """
    return Situation_contrat(contrats, date or datetime.date.today())["contrat"]


def Texte_periode_contrat(contrat=None):
    if not contrat:
        return ""
    if contrat.date_fin:
        return "du %s au %s" % (contrat.date_debut.strftime("%d/%m/%Y"), contrat.date_fin.strftime("%d/%m/%Y"))
    return "depuis le %s" % contrat.date_debut.strftime("%d/%m/%Y")


def Lignes_selection_collaborateurs(collaborateurs=[], date_reference=None):
    """ Lignes du tableau de sélection de la page d'édition """
    contrats = Get_contrats(collaborateurs)
    lignes = []
    for collaborateur in collaborateurs:
        contrat = Get_situation(contrats.get(collaborateur.pk, []), date_reference)
        lignes.append({"id": collaborateur.pk, "idcollaborateur": collaborateur.pk, "colonnes": [
            collaborateur.Get_nom(),
            contrat.type_poste.nom if contrat else "",
            ", ".join(groupe.nom for groupe in collaborateur.groupes.all()),
            Texte_periode_contrat(contrat),
        ]})
    return lignes


# ------------------------------------------------- Mise en forme -------------------------------------------------

def Style(nom="normal", taille=8, gras=False, couleur=None, alignement=None, interligne=None):
    style = ParagraphStyle(nom, fontName=FONT_BOLD if gras else FONT, fontSize=taille, leading=interligne or taille * 1.25)
    if couleur:
        style.textColor = couleur
    if alignement == "centre":
        style.alignment = TA_CENTER
    elif alignement == "droite":
        style.alignment = TA_RIGHT
    return style


def P(texte="", style=None):
    """ Paragraphe avec échappement des caractères spéciaux """
    from django.utils.html import escape
    return Paragraph(escape(str(texte if texte is not None else "")).replace("\n", "<br/>"), style or Style())


def PM(texte="", style=None):
    """ Paragraphe contenant des balises de mise en forme (le texte variable doit déjà être échappé) """
    return Paragraph(texte, style or Style())


def E(texte=""):
    """ Echappement d'un texte variable inséré dans un paragraphe PM """
    from django.utils.html import escape
    return escape(str(texte if texte is not None else ""))


def Date(date=None):
    return date.strftime("%d/%m/%Y") if date else ""


def Duree(minutes=0, vide_si_zero=True):
    if minutes is None or (vide_si_zero and abs(minutes) < 0.5):
        return ""
    signe = "-" if minutes < 0 else ""
    minutes = int(round(abs(minutes)))
    return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)


def Nombre(valeur=0):
    return ("%.2f" % valeur).rstrip("0").rstrip(".").replace(".", ",") if valeur else "0"


def Chemin_photo(collaborateur=None):
    """ Chemin du fichier de la photo, ou de l'image par défaut """
    if collaborateur.photo:
        try:
            if os.path.isfile(collaborateur.photo.path):
                return collaborateur.photo.path
        except (ValueError, NotImplementedError):
            pass
    nom_image = "images/%s.png" % ("homme" if collaborateur.civilite == "M" else "femme")
    chemin = os.path.join(settings.STATIC_ROOT, nom_image)
    if os.path.isfile(chemin):
        return chemin
    from django.contrib.staticfiles import finders
    return finders.find(nom_image)


def Image_photo(collaborateur=None, largeur=20 * mm, hauteur=25 * mm):
    """ Photo redimensionnée en conservant les proportions, centrée dans un cadre de taille fixe """
    contenu = ""
    chemin = Chemin_photo(collaborateur)
    if chemin:
        try:
            from PIL import Image as PILImage
            with PILImage.open(chemin) as image:
                l, h = image.size
            ratio = min(largeur / l, hauteur / h)
            contenu = Image(chemin, width=l * ratio, height=h * ratio)
        except Exception:
            contenu = ""
    cadre = Table([[contenu]], [largeur], [hauteur])
    cadre.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return cadre


def Style_tableau(entete=True, zebra=True, taille=8, nbre_lignes=0, padding=3):
    regles = [
        ("FONT", (0, 0), (-1, -1), FONT, taille),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, COULEUR_TRAIT),
        ("TOPPADDING", (0, 0), (-1, -1), padding), ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if entete:
        regles += [("BACKGROUND", (0, 0), (-1, 0), COULEUR_ENTETE), ("FONT", (0, 0), (-1, 0), FONT_BOLD, taille)]
    if zebra and nbre_lignes:
        for index in range(1 + (1 if entete else 0), nbre_lignes, 2):
            regles.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#F8F9FA")))
    return TableStyle(regles)


def Titre_section(texte="", largeur=None):
    """ Bandeau de titre de section """
    tableau = Table([[P(texte, Style("section", 9.5, gras=True, couleur=colors.white))]], [largeur])
    tableau.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), COULEUR_PRINCIPALE), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    return tableau


def Zone_signatures(libelles=[], largeur=None, hauteur=22 * mm):
    """ Cadres de signature côte à côte """
    nbre = len(libelles)
    largeur_cadre = (largeur - (nbre - 1) * 8 * mm) / nbre
    donnees, colonnes = [[]], []
    for index, libelle in enumerate(libelles):
        if index:
            donnees[0].append("")
            colonnes.append(8 * mm)
        donnees[0].append(P(libelle, Style("signature", 8)))
        colonnes.append(largeur_cadre)
    tableau = Table(donnees, colonnes, rowHeights=[hauteur])
    regles = [("VALIGN", (0, 0), (-1, -1), "TOP")]
    for index in range(0, len(colonnes), 2):
        regles.append(("BOX", (index, 0), (index, 0), 0.5, COULEUR_TRAIT))
    tableau.setStyle(TableStyle(regles))
    return tableau


def Get_organisateur():
    return Organisateur.objects.filter(pk=1).first() or Organisateur.objects.first()


class Impression_edition(Impression):
    """ Impression avec marges standard et pied de page numéroté """
    marges = (12 * mm, 12 * mm, 14 * mm, 14 * mm)   # gauche, droite, haut, bas

    def Generation_document(self, dict_donnees={}):
        import uuid
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.lib.pagesizes import A4
        from core.utils import utils_fichiers
        self.dict_donnees = dict_donnees
        self.erreurs = []
        utils_fichiers.GetTempRep()
        self.nom_fichier = "/temp/%s.pdf" % uuid.uuid4()
        self.chemin_fichier = settings.MEDIA_ROOT + self.nom_fichier
        if not self.taille_page:
            self.taille_page = A4
        gauche, droite, haut, bas = self.marges
        self.largeur_utile = self.taille_page[0] - gauche - droite
        self.doc = SimpleDocTemplate(self.chemin_fichier, pagesize=self.taille_page, leftMargin=gauche, rightMargin=droite, topMargin=haut, bottomMargin=bas,
                                     title=self.titre, author="Noethysweb")
        self.story = []
        self.organisateur = Get_organisateur()
        self.Draw()
        if not self.story:
            self.story.append(P("Aucune donnée à imprimer."))
        self.doc.build(self.story, onFirstPage=self.Pied_page, onLaterPages=self.Pied_page)

    def Pied_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(COULEUR_TEXTE_CLAIR)
        gauche, droite, haut, bas = self.marges
        texte = "%s - %s" % (self.organisateur.nom if self.organisateur else "", self.titre)
        canvas.drawString(gauche, bas / 2, texte)
        canvas.drawRightString(self.taille_page[0] - droite, bas / 2, "Page %d - Edité le %s" % (doc.page, datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")))
        canvas.restoreState()

    def Entete(self, titre="", sous_titre="", espace_apres=6 * mm):
        """ En-tête : titre à gauche, organisateur à droite """
        organisateur = self.organisateur
        coordonnees = []
        if organisateur:
            coordonnees = [organisateur.nom or ""]
            adresse = " ".join(valeur for valeur in (organisateur.rue, organisateur.cp, organisateur.ville) if valeur)
            if adresse:
                coordonnees.append(adresse)
            contact = " - ".join(valeur for valeur in (organisateur.tel, organisateur.mail) if valeur)
            if contact:
                coordonnees.append(contact)
        bloc_titre = [P(titre, Style("titre", 15, gras=True))]
        if sous_titre:
            bloc_titre.append(P(sous_titre, Style("sous_titre", 9, couleur=COULEUR_TEXTE_CLAIR)))
        tableau = Table([[bloc_titre, P("\n".join(coordonnees), Style("organisateur", 7.5, couleur=COULEUR_TEXTE_CLAIR, alignement="droite"))]],
                        [self.largeur_utile * 0.62, self.largeur_utile * 0.38])
        tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, COULEUR_PRINCIPALE),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        self.story.append(tableau)
        self.story.append(Spacer(0, espace_apres))
