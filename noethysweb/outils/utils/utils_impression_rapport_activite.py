# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Rendu PDF (ReportLab) du rapport d'activité à partir de la structure produite par utils_rapport_activite.
"""

import logging, re, uuid, datetime, io
logger = logging.getLogger(__name__)
from xml.sax.saxutils import escape
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, CondPageBreak, NextPageTemplate, Flowable
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.widgets.markers import makeMarker
from core.utils import utils_fichiers
from outils.utils.utils_rapport_activite import Format_nombre, Evolution

POLICES = {
    "helvetica": ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"),
    "times": ("Times-Roman", "Times-Bold", "Times-Italic"),
}
PALETTE_SECONDAIRE = ["#1D9E75", "#EF9F27", "#D85A30", "#7F77DD", "#888780", "#639922", "#D4537E", "#85B7EB", "#5F5E5A"]
COULEUR_TEXTE = HexColor("#2C2C2A")
COULEUR_TEXTE_SECONDAIRE = HexColor("#5F5E5A")
COULEUR_TEXTE_DISCRET = HexColor("#888780")
COULEUR_TRAIT = HexColor("#D3D1C7")
COULEUR_FOND_ANALYSE = HexColor("#F4F3EF")
COULEUR_HAUSSE = HexColor("#3B6D11")
COULEUR_BAISSE = HexColor("#A32D2D")
MARGE_GAUCHE = MARGE_DROITE = 1.8 * cm
MARGE_HAUT = 2.2 * cm
MARGE_BAS = 1.9 * cm
REGEX_NUMERIQUE = re.compile(r"^[+\-]?[\d\u00a0\u202f\s.,]+(\s?(%|€|pt|pts|h\d\d|jours?|\S{1,3}))?$")


def Melanger(couleur, autre, proportion):
    """ Mélange deux couleurs : proportion = part de 'autre' """
    return Color(couleur.red + (autre.red - couleur.red) * proportion,
                 couleur.green + (autre.green - couleur.green) * proportion,
                 couleur.blue + (autre.blue - couleur.blue) * proportion)


def Teinte(couleur, proportion_blanc=0.85):
    return Melanger(couleur, colors.white, proportion_blanc)


def Ombre(couleur, proportion_noir=0.35):
    return Melanger(couleur, colors.black, proportion_noir)


def Hex_valide(valeur, defaut):
    if valeur and re.match(r"^#[0-9a-fA-F]{6}$", valeur.strip()):
        return valeur.strip()
    return defaut


def Format_compact(valeur, format="entier"):
    """ Format court pour les étiquettes de graphiques """
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return ""
    if format == "pourcent":
        return Format_nombre(valeur, "decimal")
    if abs(valeur) >= 1000000:
        return Format_nombre(valeur / 1000000, "decimal") + " M"
    if abs(valeur) >= 10000:
        return Format_nombre(valeur / 1000, "decimal") + " k"
    if format == "decimal" and valeur != int(valeur):
        return Format_nombre(valeur, "decimal")
    return Format_nombre(valeur, "entier")


class Options():
    def __init__(self, **kwargs):
        self.titre = kwargs.get("titre") or "Rapport d'activité"
        self.sous_titre = kwargs.get("sous_titre") or ""
        self.introduction = kwargs.get("introduction") or ""
        self.pied_page = kwargs.get("pied_page") or ""
        self.organisateur = kwargs.get("organisateur") or ""
        self.auteur = kwargs.get("auteur") or ""
        self.couleur_principale = HexColor(Hex_valide(kwargs.get("couleur_principale"), "#185FA5"))
        self.couleur_comparaison = HexColor(Hex_valide(kwargs.get("couleur_comparaison"), "#B4B2A9"))
        polices = POLICES.get(kwargs.get("police"), POLICES["helvetica"])
        self.police, self.police_gras, self.police_italique = polices
        self.taille = max(7, min(12, int(kwargs.get("taille") or 9)))
        self.style_garde = kwargs.get("style_garde") or "bandeau"
        self.logo = kwargs.get("logo")  # bytes ou None
        self.sommaire = kwargs.get("sommaire", True)
        self.numeros_page = kwargs.get("numeros_page", True)
        self.valeurs_graphiques = kwargs.get("valeurs_graphiques", True)
        self.periode = kwargs.get("periode") or ""
        self.periode_comparaison = kwargs.get("periode_comparaison") or ""
        self.activites = kwargs.get("activites") or ""
        self.symbole = kwargs.get("symbole") or "€"


# ------------------------------------------------------------------------------------------------------
# Document
# ------------------------------------------------------------------------------------------------------

def Canvas_numerote(options):
    """ Canvas qui connaît le nombre total de pages pour afficher 'Page x / y' """

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            rl_canvas.Canvas.__init__(self, *args, **kwargs)
            self._etats_pages = []
            self._numeroter_page = False

        def showPage(self):
            self._etats_pages.append(dict(self.__dict__))
            self._startPage()
            self._numeroter_page = False

        def save(self):
            nbre_pages = len(self._etats_pages)
            for etat in self._etats_pages:
                self.__dict__.update(etat)
                if options.numeros_page and etat.get("_numeroter_page"):
                    self.setFont(options.police, options.taille - 1.5)
                    self.setFillColor(COULEUR_TEXTE_DISCRET)
                    self.drawRightString(A4[0] - MARGE_DROITE, MARGE_BAS - 0.95 * cm, "Page %d / %d" % (self._pageNumber, nbre_pages))
                rl_canvas.Canvas.showPage(self)
            rl_canvas.Canvas.save(self)

    return NumberedCanvas


class Document(BaseDocTemplate):
    def __init__(self, chemin, options=None, **kwargs):
        BaseDocTemplate.__init__(self, chemin, pagesize=A4, leftMargin=MARGE_GAUCHE, rightMargin=MARGE_DROITE, topMargin=MARGE_HAUT,
                                 bottomMargin=MARGE_BAS, title=options.titre, author=options.auteur, subject="Rapport d'activité", creator="Noethysweb", **kwargs)
        self.options = options
        frame_garde = Frame(0, 0, A4[0], A4[1], id="garde", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        frame_contenu = Frame(MARGE_GAUCHE, MARGE_BAS, A4[0] - MARGE_GAUCHE - MARGE_DROITE, A4[1] - MARGE_HAUT - MARGE_BAS, id="contenu",
                              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        templates = [PageTemplate(id="garde", frames=[frame_garde], onPage=self.Dessiner_garde),
                     PageTemplate(id="contenu", frames=[frame_contenu], onPage=self.Dessiner_entete_pied)]
        # Sans page de garde, la première page utilise directement le gabarit de contenu
        if options.style_garde not in ("bandeau", "sobre"):
            templates.reverse()
        self.addPageTemplates(templates)
        self.compteur_signets = 0

    def afterFlowable(self, flowable):
        """ Alimente le sommaire et les signets PDF """
        if isinstance(flowable, Paragraph) and getattr(flowable, "_rubrique", False):
            texte = flowable.getPlainText()
            self.compteur_signets += 1
            cle = "rubrique_%d" % self.compteur_signets
            self.canv.bookmarkPage(cle)
            self.canv.addOutlineEntry(texte, cle, level=0, closed=False)
            self.notify("TOCEntry", (0, texte, self.page, cle))

    def handle_documentBegin(self):
        self.compteur_signets = 0
        BaseDocTemplate.handle_documentBegin(self)

    # --------------------------------- Page de garde ---------------------------------

    def Dessiner_logo(self, canvas, x, y_haut, largeur_max=4.2 * cm, hauteur_max=2.2 * cm, fond_blanc=False):
        if not self.options.logo:
            return 0
        try:
            image = ImageReader(io.BytesIO(self.options.logo))
            largeur, hauteur = image.getSize()
            ratio = min(largeur_max / largeur, hauteur_max / hauteur)
            l, h = largeur * ratio, hauteur * ratio
            if fond_blanc:
                canvas.setFillColor(colors.white)
                canvas.roundRect(x - 0.25 * cm, y_haut - h - 0.25 * cm, l + 0.5 * cm, h + 0.5 * cm, 0.15 * cm, stroke=0, fill=1)
            canvas.drawImage(image, x, y_haut - h, l, h, mask="auto", preserveAspectRatio=True)
            return h
        except Exception:
            logger.exception("Rapport d'activité : logo illisible")
            return 0

    def Dessiner_paragraphe(self, canvas, texte, style, x, y_haut, largeur):
        paragraphe = Paragraph(texte, style)
        l, h = paragraphe.wrapOn(canvas, largeur, A4[1])
        paragraphe.drawOn(canvas, x, y_haut - h)
        return h

    def Dessiner_garde(self, canvas, doc):
        o = self.options
        canvas.saveState()
        largeur_page, hauteur_page = A4
        x = 2.4 * cm
        largeur_texte = largeur_page - 2 * x
        couleur = o.couleur_principale
        style_titre = ParagraphStyle("garde_titre", fontName=o.police_gras, fontSize=28, leading=33, textColor=colors.white if o.style_garde == "bandeau" else couleur)
        style_sous_titre = ParagraphStyle("garde_sous_titre", fontName=o.police, fontSize=12, leading=15, textColor=Teinte(couleur, 0.7) if o.style_garde == "bandeau" else COULEUR_TEXTE_SECONDAIRE)
        style_periode = ParagraphStyle("garde_periode", fontName=o.police_gras, fontSize=12.5, leading=16, textColor=couleur)
        style_info = ParagraphStyle("garde_info", fontName=o.police, fontSize=10, leading=14, textColor=COULEUR_TEXTE_SECONDAIRE)
        style_intro = ParagraphStyle("garde_intro", fontName=o.police_italique, fontSize=10.5, leading=15, textColor=COULEUR_TEXTE)

        if o.style_garde == "bandeau":
            hauteur_bandeau = hauteur_page * 0.42
            canvas.setFillColor(couleur)
            canvas.rect(0, hauteur_page - hauteur_bandeau, largeur_page, hauteur_bandeau, stroke=0, fill=1)
            canvas.setFillColor(Ombre(couleur, 0.25))
            canvas.rect(0, hauteur_page - hauteur_bandeau, largeur_page, 0.25 * cm, stroke=0, fill=1)
            self.Dessiner_logo(canvas, x, hauteur_page - 2.2 * cm, fond_blanc=True)
            # Titre et sous-titre en bas du bandeau
            paragraphe = Paragraph(escape(o.titre), style_titre)
            l, h_titre = paragraphe.wrapOn(canvas, largeur_texte, hauteur_page)
            y_titre = hauteur_page - hauteur_bandeau + 1.4 * cm
            paragraphe.drawOn(canvas, x, y_titre)
            texte_haut = escape(o.sous_titre or o.organisateur)
            if texte_haut:
                self.Dessiner_paragraphe(canvas, texte_haut, style_sous_titre, x, y_titre + h_titre + 0.9 * cm, largeur_texte)
            y = hauteur_page - hauteur_bandeau - 1.6 * cm
        else:
            y = hauteur_page - 2.2 * cm
            if o.logo:
                y -= self.Dessiner_logo(canvas, x, y) + 0.4 * cm
            y = min(y, hauteur_page * 0.58)
            texte_haut = escape(o.sous_titre or o.organisateur)
            if texte_haut:
                y -= self.Dessiner_paragraphe(canvas, texte_haut, style_sous_titre, x, y, largeur_texte) + 0.3 * cm
            y -= self.Dessiner_paragraphe(canvas, escape(o.titre), style_titre, x, y, largeur_texte) + 0.45 * cm
            canvas.setStrokeColor(couleur)
            canvas.setLineWidth(2.5)
            canvas.line(x, y, x + largeur_texte * 0.35, y)
            y -= 0.9 * cm

        # Période et informations
        y -= self.Dessiner_paragraphe(canvas, escape(o.periode), style_periode, x, y, largeur_texte) + 0.2 * cm
        if o.periode_comparaison:
            y -= self.Dessiner_paragraphe(canvas, escape(o.periode_comparaison), style_info, x, y, largeur_texte) + 0.15 * cm
        if o.activites:
            y -= self.Dessiner_paragraphe(canvas, escape(o.activites), style_info, x, y, largeur_texte) + 0.2 * cm
        if o.sous_titre and o.organisateur:
            y -= self.Dessiner_paragraphe(canvas, escape(o.organisateur), style_info, x, y, largeur_texte) + 0.2 * cm

        # Introduction
        if o.introduction:
            y -= 0.6 * cm
            texte = "<br/>".join(escape(ligne) for ligne in o.introduction.splitlines())
            paragraphe = Paragraph(texte, style_intro)
            l, h = paragraphe.wrapOn(canvas, largeur_texte - 0.5 * cm, hauteur_page)
            h = min(h, y - 3 * cm)
            paragraphe.drawOn(canvas, x + 0.5 * cm, y - h)
            canvas.setStrokeColor(couleur)
            canvas.setLineWidth(2)
            canvas.line(x, y, x, y - h)

        # Pied de la page de garde
        canvas.setFont(o.police, 8.5)
        canvas.setFillColor(COULEUR_TEXTE_DISCRET)
        texte = "Document édité le %s" % datetime.date.today().strftime("%d/%m/%Y")
        if o.auteur:
            texte += " par %s" % o.auteur
        canvas.drawString(x, 1.5 * cm, texte)
        canvas.drawRightString(largeur_page - x, 1.5 * cm, "Noethysweb")
        canvas.restoreState()

    # --------------------------------- Entête et pied de page ---------------------------------

    def Dessiner_entete_pied(self, canvas, doc):
        o = self.options
        canvas.saveState()
        largeur_page, hauteur_page = A4
        canvas._numeroter_page = True
        # Entête
        canvas.setFont(o.police, o.taille - 1.5)
        canvas.setFillColor(COULEUR_TEXTE_DISCRET)
        y = hauteur_page - MARGE_HAUT + 0.75 * cm
        canvas.drawString(MARGE_GAUCHE, y, o.titre[:90])
        if o.organisateur:
            canvas.drawRightString(largeur_page - MARGE_DROITE, y, o.organisateur[:70])
        canvas.setStrokeColor(COULEUR_TRAIT)
        canvas.setLineWidth(0.5)
        canvas.line(MARGE_GAUCHE, y - 0.2 * cm, largeur_page - MARGE_DROITE, y - 0.2 * cm)
        # Pied
        y = MARGE_BAS - 0.6 * cm
        canvas.setStrokeColor(o.couleur_principale)
        canvas.setLineWidth(1)
        canvas.line(MARGE_GAUCHE, y, MARGE_GAUCHE + 1.2 * cm, y)
        canvas.setFillColor(COULEUR_TEXTE_DISCRET)
        canvas.setFont(o.police, o.taille - 1.5)
        canvas.drawString(MARGE_GAUCHE, y - 0.35 * cm, (o.pied_page or o.organisateur)[:110])
        canvas.restoreState()


# ------------------------------------------------------------------------------------------------------
# Impression
# ------------------------------------------------------------------------------------------------------

class Impression():
    def __init__(self, rubriques=[], options=None):
        self.rubriques = rubriques
        self.o = options or Options()
        self.erreurs = []
        utils_fichiers.GetTempRep()
        self.nom_fichier = "/temp/%s.pdf" % uuid.uuid4()
        self.chemin_fichier = settings.MEDIA_ROOT + self.nom_fichier
        self.largeur = A4[0] - MARGE_GAUCHE - MARGE_DROITE
        self.Creer_styles()
        try:
            self.Generer()
        except Exception as err:
            logger.exception("Rapport d'activité : erreur lors de la génération du PDF")
            self.erreurs.append("Erreur lors de la génération du PDF : %s" % err)

    def Get_nom_fichier(self):
        return self.nom_fichier

    def Creer_styles(self):
        o, t = self.o, self.o.taille
        c = o.couleur_principale
        self.styles = {
            "normal": ParagraphStyle("normal", fontName=o.police, fontSize=t, leading=t * 1.4, textColor=COULEUR_TEXTE),
            "rubrique": ParagraphStyle("rubrique", fontName=o.police_gras, fontSize=t * 1.75, leading=t * 2.1, textColor=Ombre(c, 0.2), spaceAfter=t * 0.4),
            "sous_titre": ParagraphStyle("sous_titre", fontName=o.police_gras, fontSize=t + 2, leading=(t + 2) * 1.3, textColor=Ombre(c, 0.15), spaceBefore=t * 0.6, spaceAfter=t * 0.5),
            "titre_bloc": ParagraphStyle("titre_bloc", fontName=o.police_gras, fontSize=t, leading=t * 1.35, textColor=c, spaceAfter=t * 0.4),
            "analyse": ParagraphStyle("analyse", fontName=o.police, fontSize=t, leading=t * 1.45, textColor=HexColor("#444441")),
            "analyse_titre": ParagraphStyle("analyse_titre", fontName=o.police_gras, fontSize=t - 0.5, leading=t * 1.3, textColor=c),
            "puce": ParagraphStyle("puce", fontName=o.police, fontSize=t, leading=t * 1.45, textColor=COULEUR_TEXTE, leftIndent=t * 1.3, bulletIndent=t * 0.3),
            "note": ParagraphStyle("note", fontName=o.police_italique, fontSize=t - 1, leading=(t - 1) * 1.35, textColor=COULEUR_TEXTE_SECONDAIRE),
            "cellule": ParagraphStyle("cellule", fontName=o.police, fontSize=t - 0.5, leading=(t - 0.5) * 1.25, textColor=COULEUR_TEXTE),
            "cellule_droite": ParagraphStyle("cellule_droite", fontName=o.police, fontSize=t - 0.5, leading=(t - 0.5) * 1.25, textColor=COULEUR_TEXTE, alignment=TA_RIGHT),
            "entete": ParagraphStyle("entete", fontName=o.police_gras, fontSize=t - 0.5, leading=(t - 0.5) * 1.25, textColor=colors.white),
            "entete_droite": ParagraphStyle("entete_droite", fontName=o.police_gras, fontSize=t - 0.5, leading=(t - 0.5) * 1.25, textColor=colors.white, alignment=TA_RIGHT),
            "kpi_valeur": ParagraphStyle("kpi_valeur", fontName=o.police_gras, fontSize=t + 5, leading=(t + 5) * 1.15, textColor=Ombre(c, 0.2)),
            "kpi_label": ParagraphStyle("kpi_label", fontName=o.police, fontSize=t - 0.5, leading=(t - 0.5) * 1.25, textColor=Ombre(c, 0.05)),
            "kpi_detail": ParagraphStyle("kpi_detail", fontName=o.police, fontSize=t - 1.5, leading=(t - 1.5) * 1.3, textColor=COULEUR_TEXTE_SECONDAIRE),
            "sommaire_titre": ParagraphStyle("sommaire_titre", fontName=o.police_gras, fontSize=t * 1.75, leading=t * 2.1, textColor=Ombre(c, 0.2), spaceAfter=t),
            "toc": ParagraphStyle("toc", fontName=o.police, fontSize=t + 1.5, leading=(t + 1.5) * 1.9, textColor=COULEUR_TEXTE, leftIndent=0, firstLineIndent=0),
            "titre_document": ParagraphStyle("titre_document", fontName=o.police_gras, fontSize=t * 2.2, leading=t * 2.6, textColor=c),
        }

    # --------------------------------- Génération ---------------------------------

    def Generer(self):
        o = self.o
        story = []

        # Page de garde
        if o.style_garde in ("bandeau", "sobre"):
            story.append(NextPageTemplate("contenu"))
            story.append(Spacer(0, 1))
            story.append(PageBreak())
        else:
            story.append(NextPageTemplate("contenu"))
            story.append(Paragraph(escape(o.titre), self.styles["titre_document"]))
            infos = [o.sous_titre, o.organisateur, o.periode, o.periode_comparaison]
            story.append(Paragraph("<br/>".join(escape(i) for i in infos if i), self.styles["normal"]))
            if o.introduction:
                story.append(Spacer(0, 8))
                story.append(self.Encadre(["<br/>".join(escape(l) for l in o.introduction.splitlines())], titre=None))
            story.append(Spacer(0, 16))

        # Sommaire
        if o.sommaire and len(self.rubriques) > 1:
            story.append(Paragraph("Sommaire", self.styles["sommaire_titre"]))
            toc = TableOfContents(dotsMinLevel=0)
            toc.levelStyles = [self.styles["toc"]]
            story.append(toc)
            story.append(PageBreak())

        # Rubriques
        for index, rubrique in enumerate(self.rubriques, 1):
            if index > 1:
                story.append(PageBreak())
            titre = Paragraph("%d. %s" % (index, escape(rubrique.titre)), self.styles["rubrique"])
            titre._rubrique = True
            story.append(titre)
            story.append(Trait(self.largeur, o.couleur_principale, 1.5))
            story.append(Spacer(0, o.taille * 0.9))
            for bloc in rubrique.blocs:
                try:
                    elements = getattr(self, "Bloc_%s" % bloc["type"])(bloc)
                except Exception as err:
                    logger.exception("Rapport d'activité : erreur de rendu d'un bloc %s" % bloc.get("type"))
                    elements = [Paragraph("Ce bloc n'a pas pu être affiché : %s" % escape(str(err)), self.styles["note"])]
                if elements:
                    story.extend(elements)
                    story.append(Spacer(0, o.taille * 1.3))

        doc = Document(self.chemin_fichier, options=o)
        doc.multiBuild(story, canvasmaker=Canvas_numerote(o))

    # --------------------------------- Blocs ---------------------------------

    def Bloc_kpis(self, bloc):
        items = bloc["items"]
        if not items:
            return []
        nbre_colonnes = min(bloc.get("colonnes", 3), len(items)) or 1
        espacement = 0.25 * cm
        largeur_cellule = (self.largeur - espacement * (nbre_colonnes - 1)) / nbre_colonnes
        cellules = []
        for item in items:
            contenu = [Paragraph(escape(Format_nombre(item["valeur"], item["format"], self.o.symbole)), self.styles["kpi_valeur"]),
                       Paragraph(escape(item["label"]), self.styles["kpi_label"])]
            details = []
            if item.get("n1") is not None:
                details.append(self.Texte_evolution(item["valeur"], item["n1"], item["format"], item.get("inverse")))
            if item.get("detail"):
                details.append(escape(item["detail"]))
            if details:
                contenu.append(Paragraph(" · ".join(details), self.styles["kpi_detail"]))
            cellules.append(contenu)
        # Grille : colonnes de cellules séparées par des colonnes d'espacement, lignes séparées par des lignes d'espacement
        lignes = []
        for index in range(0, len(cellules), nbre_colonnes):
            bloc_cellules = cellules[index:index + nbre_colonnes]
            ligne = []
            for i in range(nbre_colonnes):
                ligne.append(bloc_cellules[i] if i < len(bloc_cellules) else "")
                if i < nbre_colonnes - 1:
                    ligne.append("")
            if lignes:
                lignes.append([""] * len(ligne))
            lignes.append(ligne)
        largeurs = [largeur_cellule if i % 2 == 0 else espacement for i in range(nbre_colonnes * 2 - 1)]
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]
        fond = Teinte(self.o.couleur_principale, 0.9)
        for index_ligne in range(0, len(lignes), 2):
            for index_colonne in range(0, nbre_colonnes * 2 - 1, 2):
                if lignes[index_ligne][index_colonne] != "":
                    style.append(("BACKGROUND", (index_colonne, index_ligne), (index_colonne, index_ligne), fond))
                    style.append(("LINEBEFORE", (index_colonne, index_ligne), (index_colonne, index_ligne), 2, self.o.couleur_principale))
        for index_ligne in range(1, len(lignes), 2):
            style.append(("TOPPADDING", (0, index_ligne), (-1, index_ligne), 0))
            style.append(("BOTTOMPADDING", (0, index_ligne), (-1, index_ligne), 0))
        hauteurs = [None if i % 2 == 0 else espacement for i in range(len(lignes))]
        tableau = Table(lignes, colWidths=largeurs, rowHeights=hauteurs)
        tableau.setStyle(TableStyle(style))
        return [tableau]

    def Texte_evolution(self, valeur, n1, format="entier", inverse=False):
        if valeur is None or n1 is None:
            return ""
        if format == "pourcent":
            ecart = float(valeur) - float(n1)
            texte = ("+" if ecart > 0 else "") + Format_nombre(ecart, "decimal") + " pt"
            signe = ecart
        else:
            evol = Evolution(valeur, n1)
            if evol is None:
                return "vs %s" % escape(Format_nombre(n1, format, self.o.symbole))
            texte = ("+" if evol > 0 else "") + Format_nombre(evol, "pourcent")
            signe = evol
        if abs(signe) < 0.05:
            couleur = COULEUR_TEXTE_SECONDAIRE
        else:
            favorable = (signe > 0) != bool(inverse)
            couleur = COULEUR_HAUSSE if favorable else COULEUR_BAISSE
        return "<font color='%s'><b>%s</b></font> vs %s" % (couleur.hexval().replace("0x", "#"), escape(texte), escape(Format_nombre(n1, format, self.o.symbole)))

    def Encadre(self, phrases=[], titre="Analyse"):
        lignes = []
        if titre:
            lignes.append([Paragraph(escape(titre).upper(), self.styles["analyse_titre"])])
        for phrase in phrases:
            lignes.append([Paragraph(phrase, self.styles["analyse"])])
        tableau = Table(lignes, colWidths=[self.largeur])
        tableau.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COULEUR_FOND_ANALYSE),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, self.o.couleur_principale),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ]))
        return tableau

    def Bloc_analyse(self, bloc):
        return [self.Encadre([escape(phrase) for phrase in bloc["phrases"]])]

    def Bloc_puces(self, bloc):
        return [Paragraph(escape(item), self.styles["puce"], bulletText="•") for item in bloc["items"]]

    def Bloc_sous_titre(self, bloc):
        return [CondPageBreak(5 * cm), Paragraph(escape(bloc["texte"]), self.styles["sous_titre"])]

    def Bloc_note(self, bloc):
        return [Paragraph(escape(bloc["texte"]), self.styles["note"])]

    # --------------------------------- Tableaux ---------------------------------

    def Formater_cellule(self, valeur, format="texte"):
        if isinstance(valeur, (int, float)) and not isinstance(valeur, bool):
            return Format_nombre(valeur, format if format != "texte" else "entier", self.o.symbole)
        if hasattr(valeur, "as_tuple"):
            return Format_nombre(float(valeur), format if format != "texte" else "decimal", self.o.symbole)
        return "" if valeur is None else str(valeur)

    def Bloc_tableau(self, bloc):
        colonnes, lignes, formats = bloc["colonnes"], bloc["lignes"], bloc.get("formats") or []
        if not lignes:
            return []
        nbre_colonnes = len(colonnes)
        formats = (formats + ["texte"] * nbre_colonnes)[:nbre_colonnes]
        textes = [[self.Formater_cellule(ligne[i] if i < len(ligne) else "", formats[i]) for i in range(nbre_colonnes)] for ligne in lignes]
        total = [self.Formater_cellule(bloc["total"][i] if i < len(bloc["total"]) else "", formats[i]) for i in range(nbre_colonnes)] if bloc.get("total") else None

        # Alignement : colonnes numériques à droite
        droite = []
        for i in range(nbre_colonnes):
            valeurs = [ligne[i] for ligne in textes if ligne[i] not in ("", "-")]
            droite.append(i > 0 and bool(valeurs) and all(REGEX_NUMERIQUE.match(v) for v in valeurs))

        # Taille de police réduite pour les tableaux larges
        taille = self.o.taille - 0.5 if nbre_colonnes <= 6 else self.o.taille - 1.5
        style_cellule = ParagraphStyle("c", parent=self.styles["cellule"], fontSize=taille, leading=taille * 1.25)
        style_droite = ParagraphStyle("cd", parent=self.styles["cellule_droite"], fontSize=taille, leading=taille * 1.25)
        style_entete = ParagraphStyle("e", parent=self.styles["entete"], fontSize=taille, leading=taille * 1.25)
        style_entete_droite = ParagraphStyle("ed", parent=self.styles["entete_droite"], fontSize=taille, leading=taille * 1.25)
        style_total = ParagraphStyle("t", parent=style_cellule, fontName=self.o.police_gras)
        style_total_droite = ParagraphStyle("td", parent=style_droite, fontName=self.o.police_gras)

        # Largeurs de colonnes
        padding = 12
        largeurs = []
        for i in range(nbre_colonnes):
            # L'entête peut passer à la ligne entre les mots : on mesure son mot le plus long
            largeur_entete = max(stringWidth(mot, self.o.police_gras, taille) for mot in (str(colonnes[i]).split() or [""]))
            contenus = [ligne[i] for ligne in textes] + ([total[i]] if total else [])
            largeur_valeurs = max([stringWidth(str(texte), self.o.police_gras, taille) for texte in contenus] + [0])
            largeurs.append(max(largeur_entete, largeur_valeurs) + padding)
        if nbre_colonnes > 1:
            for i in range(1, nbre_colonnes):
                largeurs[i] = min(max(largeurs[i], 1.4 * cm), 5 * cm)
            reste = self.largeur - sum(largeurs[1:])
            largeurs[0] = max(min(largeurs[0], reste), min(5 * cm, reste)) if reste > 2 * cm else 2 * cm
            if sum(largeurs) > self.largeur or largeurs[0] < self.largeur * 0.25:
                # On réduit proportionnellement les colonnes numériques
                largeurs[0] = max(largeurs[0], self.largeur * 0.28)
                facteur = (self.largeur - largeurs[0]) / sum(largeurs[1:])
                largeurs[1:] = [l * min(facteur, 1) for l in largeurs[1:]]
            # Si le tableau est étroit, on l'élargit à toute la largeur quand il a beaucoup de colonnes
            if sum(largeurs) < self.largeur * 0.75 and nbre_colonnes >= 4:
                largeurs[0] += self.largeur - sum(largeurs)
        else:
            largeurs = [self.largeur]

        # Données
        index_evol = [i for i, c in enumerate(colonnes) if c.startswith("Évol")]
        donnees = [[Paragraph(escape(str(c)), style_entete_droite if droite[i] else style_entete) for i, c in enumerate(colonnes)]]
        for ligne in textes:
            cellules = []
            for i, texte in enumerate(ligne):
                contenu = escape(texte)
                if i in index_evol and texte not in ("", "-"):
                    couleur = COULEUR_HAUSSE if texte.startswith("+") else (COULEUR_BAISSE if texte.startswith("-") else COULEUR_TEXTE)
                    contenu = "<font color='%s'>%s</font>" % (couleur.hexval().replace("0x", "#"), contenu)
                cellules.append(Paragraph(contenu, style_droite if droite[i] else style_cellule))
            donnees.append(cellules)
        if total:
            donnees.append([Paragraph(escape(texte), style_total_droite if droite[i] else style_total) for i, texte in enumerate(total)])

        c = self.o.couleur_principale
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), c),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, COULEUR_TRAIT),
        ]
        for index in range(2, len(donnees), 2):
            style.append(("BACKGROUND", (0, index), (-1, index), Teinte(c, 0.95)))
        if total:
            style += [("BACKGROUND", (0, -1), (-1, -1), Teinte(c, 0.82)), ("LINEABOVE", (0, -1), (-1, -1), 1, c)]
        tableau = Table(donnees, colWidths=largeurs, repeatRows=1, hAlign="LEFT")
        tableau.setStyle(TableStyle(style))

        elements = []
        if bloc.get("titre"):
            elements.append(Paragraph(escape(bloc["titre"]), self.styles["titre_bloc"]))
        elements.append(tableau)
        if bloc.get("note"):
            elements.append(Spacer(0, 3))
            elements.append(Paragraph(escape(bloc["note"]), self.styles["note"]))
        if len(donnees) <= 22:
            return [KeepTogether(elements)]
        return [CondPageBreak(6 * cm)] + elements

    # --------------------------------- Graphiques ---------------------------------

    def Couleur_serie(self, serie, index=0, series=None):
        if serie.get("role") == "comparaison":
            return self.o.couleur_comparaison
        # Rang de la série parmi les séries principales (la première prend la couleur principale)
        rang = [s for s in (series or [serie]) if s.get("role") != "comparaison"].index(serie) if series else 0
        return self.o.couleur_principale if rang == 0 else HexColor(PALETTE_SECONDAIRE[(rang - 1) % len(PALETTE_SECONDAIRE)])

    def Legende(self, drawing, series, x, y):
        """ Légende horizontale en haut à droite """
        taille = self.o.taille - 1.5
        position = x
        elements = []
        for serie in series:
            largeur = 9 + 4 + stringWidth(serie["nom"], self.o.police, taille) + 12
            elements.append((serie, largeur))
        position = x - sum(l for s, l in elements)
        for index, (serie, largeur) in enumerate(elements):
            drawing.add(Rect(position, y, 8, 8, fillColor=self.Couleur_serie(serie, 0, series), strokeColor=None))
            drawing.add(String(position + 12, y + 1, serie["nom"], fontName=self.o.police, fontSize=taille, fillColor=COULEUR_TEXTE_SECONDAIRE))
            position += largeur

    def Etiquettes(self, series, format=None):
        """ Etiquettes de valeurs : uniquement pour les séries principales et les valeurs non nulles """
        return [[Format_compact(v, format) if v and s.get("role") != "comparaison" else "" for v in s["valeurs"]] for s in series]

    def Titre_graphique(self, titre):
        return Paragraph(escape(titre), self.styles["titre_bloc"]) if titre else None

    def Bloc_barres(self, bloc):
        labels, series = bloc["labels"], [s for s in bloc["series"] if s["valeurs"]]
        if not labels or not series or not any(any(s["valeurs"]) for s in series):
            return []
        # Ordre : comparaison d'abord (à gauche), principal ensuite
        series = sorted(series, key=lambda s: 0 if s.get("role") == "comparaison" else 1)
        if bloc.get("horizontal"):
            return self.Barres_horizontales(bloc, labels, series)

        taille = self.o.taille - 1.5
        hauteur = 6.2 * cm
        drawing = Drawing(self.largeur, hauteur)
        longueur_max = max(stringWidth(l, self.o.police, taille) for l in labels)
        largeur_categorie = (self.largeur - 50) / len(labels)
        rotation = longueur_max > largeur_categorie - 4
        marge_bas = 18 if not rotation else min(70, 12 + longueur_max * 0.7)
        chart = VerticalBarChart()
        chart.x, chart.y = 45, marge_bas
        chart.width, chart.height = self.largeur - 55, hauteur - marge_bas - (24 if len(series) > 1 else 12)
        chart.data = [tuple(s["valeurs"]) for s in series]
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.fontName = self.o.police
        chart.categoryAxis.labels.fontSize = taille
        chart.categoryAxis.labels.fillColor = COULEUR_TEXTE_SECONDAIRE
        if rotation:
            chart.categoryAxis.labels.angle = 35
            chart.categoryAxis.labels.boxAnchor = "ne"
            chart.categoryAxis.labels.dx, chart.categoryAxis.labels.dy = 2, -2
        chart.categoryAxis.strokeColor = COULEUR_TEXTE_DISCRET
        chart.categoryAxis.tickDown = 0
        self.Configurer_axe_valeurs(chart.valueAxis, series, bloc.get("format"))
        chart.barSpacing = 1
        chart.groupSpacing = max(2, min(12, largeur_categorie * 0.25))
        for index, serie in enumerate(series):
            chart.bars[index].fillColor = self.Couleur_serie(serie, index, series)
            chart.bars[index].strokeColor = None
        chart.bars.strokeWidth = 0
        if self.o.valeurs_graphiques and len(labels) <= 26:
            chart.barLabelFormat = "values"
            chart.barLabelArray = self.Etiquettes(series, bloc.get("format"))
            chart.barLabels.fontName = self.o.police
            chart.barLabels.fontSize = taille - 0.5
            chart.barLabels.fillColor = COULEUR_TEXTE_SECONDAIRE
            chart.barLabels.nudge = 6
        drawing.add(chart)
        if len(series) > 1:
            self.Legende(drawing, series, self.largeur, hauteur - 10)
        return [KeepTogether([e for e in (self.Titre_graphique(bloc.get("titre")), drawing) if e])]

    def Configurer_axe_valeurs(self, axe, series, format=None):
        maximum = max([max(s["valeurs"] or [0]) for s in series] + [0])
        axe.valueMin = 0
        if maximum <= 0:
            axe.valueMax = 1
        elif format == "pourcent" and maximum <= 100:
            axe.valueMax = min(100, maximum * 1.18) if maximum > 5 else maximum * 1.3
        else:
            axe.valueMax = maximum * 1.15
        if maximum and maximum < 5 and format not in ("pourcent", "montant", "decimal"):
            axe.valueStep = 1
            axe.valueMax = max(axe.valueMax, maximum + 1)
        axe.labels.fontName = self.o.police
        axe.labels.fontSize = self.o.taille - 1.5
        axe.labels.fillColor = COULEUR_TEXTE_DISCRET
        axe.labelTextFormat = lambda v: Format_compact(v, format)
        axe.strokeColor = None
        axe.visibleGrid = True
        axe.gridStrokeColor = HexColor("#E8E6DF")
        axe.gridStrokeWidth = 0.5
        if hasattr(axe, "tickLeft"):
            axe.tickLeft = 0
        else:
            axe.tickDown = 0

    def Barres_horizontales(self, bloc, labels, series):
        taille = self.o.taille - 1.5
        labels = list(reversed(labels))
        donnees = [tuple(reversed(s["valeurs"])) for s in series]
        largeur_labels = min(max(stringWidth(l, self.o.police, taille) for l in labels) + 8, self.largeur * 0.42)
        # Troncature des libellés trop longs
        labels_affiches = []
        for label in labels:
            while stringWidth(label, self.o.police, taille) > largeur_labels - 8 and len(label) > 4:
                label = label[:-2]
                if not label.endswith("…"):
                    label = label.rstrip() + "…"
            labels_affiches.append(label)
        hauteur_categorie = 0.48 * cm * (1 + 0.6 * (len(series) - 1))
        hauteur = max(3 * cm, len(labels) * hauteur_categorie + 30 + (14 if len(series) > 1 else 0))
        drawing = Drawing(self.largeur, hauteur)
        chart = HorizontalBarChart()
        chart.x, chart.y = largeur_labels, 18
        chart.width, chart.height = self.largeur - largeur_labels - 40, hauteur - 28 - (14 if len(series) > 1 else 0)
        chart.data = donnees
        chart.categoryAxis.categoryNames = labels_affiches
        chart.categoryAxis.labels.fontName = self.o.police
        chart.categoryAxis.labels.fontSize = taille
        chart.categoryAxis.labels.fillColor = COULEUR_TEXTE_SECONDAIRE
        chart.categoryAxis.labels.boxAnchor = "e"
        chart.categoryAxis.labels.dx = -4
        chart.categoryAxis.strokeColor = COULEUR_TEXTE_DISCRET
        chart.categoryAxis.tickLeft = 0
        self.Configurer_axe_valeurs(chart.valueAxis, series, bloc.get("format"))
        chart.valueAxis.visibleGrid = True
        chart.barSpacing = 1
        chart.groupSpacing = 4
        for index, serie in enumerate(series):
            chart.bars[index].fillColor = self.Couleur_serie(serie, index, series)
            chart.bars[index].strokeColor = None
        if self.o.valeurs_graphiques:
            chart.barLabelFormat = "values"
            chart.barLabelArray = [list(reversed(etiquettes)) for etiquettes in self.Etiquettes(series, bloc.get("format"))]
            chart.barLabels.fontName = self.o.police
            chart.barLabels.fontSize = taille - 0.5
            chart.barLabels.fillColor = COULEUR_TEXTE_SECONDAIRE
            chart.barLabels.boxAnchor = "w"
            chart.barLabels.dx = 3
        drawing.add(chart)
        if len(series) > 1:
            self.Legende(drawing, series, self.largeur, hauteur - 10)
        elements = [e for e in (self.Titre_graphique(bloc.get("titre")), drawing) if e]
        return [KeepTogether(elements)]

    def Bloc_courbe(self, bloc):
        labels, series = bloc["labels"], [s for s in bloc["series"] if s["valeurs"]]
        if not labels or not series:
            return []
        series = sorted(series, key=lambda s: 0 if s.get("role") == "comparaison" else 1)
        taille = self.o.taille - 1.5
        hauteur = 5.6 * cm
        drawing = Drawing(self.largeur, hauteur)
        chart = HorizontalLineChart()
        chart.x, chart.y = 45, 18
        chart.width, chart.height = self.largeur - 55, hauteur - 18 - (24 if len(series) > 1 else 12)
        chart.data = [tuple(s["valeurs"]) for s in series]
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.fontName = self.o.police
        chart.categoryAxis.labels.fontSize = taille
        chart.categoryAxis.labels.fillColor = COULEUR_TEXTE_SECONDAIRE
        chart.categoryAxis.strokeColor = COULEUR_TEXTE_DISCRET
        chart.categoryAxis.tickDown = 0
        self.Configurer_axe_valeurs(chart.valueAxis, series, bloc.get("format"))
        for index, serie in enumerate(series):
            couleur = self.Couleur_serie(serie, index, series)
            chart.lines[index].strokeColor = couleur
            chart.lines[index].strokeWidth = 2 if serie.get("role") != "comparaison" else 1.5
            chart.lines[index].symbol = makeMarker("FilledCircle", size=3.5, fillColor=couleur, strokeColor=couleur)
        if self.o.valeurs_graphiques and len(labels) <= 14:
            chart.lineLabelFormat = "values"
            chart.lineLabelArray = self.Etiquettes(series, bloc.get("format"))
            chart.lineLabels.fontName = self.o.police
            chart.lineLabels.fontSize = taille - 0.5
            chart.lineLabels.fillColor = COULEUR_TEXTE_SECONDAIRE
            chart.lineLabels.dy = 6
        drawing.add(chart)
        if len(series) > 1:
            self.Legende(drawing, series, self.largeur, hauteur - 10)
        return [KeepTogether([e for e in (self.Titre_graphique(bloc.get("titre")), drawing) if e])]

    def Bloc_camembert(self, bloc):
        items = [(l, v) for l, v in zip(bloc["labels"], bloc["valeurs"]) if v and v > 0]
        if not items:
            return []
        total = sum(v for l, v in items)
        taille = self.o.taille - 1
        diametre = 4.3 * cm
        hauteur = max(diametre + 0.6 * cm, len(items) * (taille * 1.9) + 0.6 * cm)
        drawing = Drawing(self.largeur, hauteur)
        pie = Pie()
        pie.x, pie.y = 0.3 * cm, (hauteur - diametre) / 2
        pie.width = pie.height = diametre
        pie.data = [v for l, v in items]
        pie.labels = None
        pie.startAngle = 90
        pie.direction = "clockwise"
        pie.slices.strokeColor = colors.white
        pie.slices.strokeWidth = 1
        couleurs = []
        for index in range(len(items)):
            couleur = self.o.couleur_principale if index == 0 else HexColor(PALETTE_SECONDAIRE[(index - 1) % len(PALETTE_SECONDAIRE)])
            couleurs.append(couleur)
            pie.slices[index].fillColor = couleur
        drawing.add(pie)

        # Légende avec valeurs et pourcentages
        x_legende = diametre + 1.4 * cm
        largeur_legende = self.largeur - x_legende
        y = hauteur / 2 + len(items) * taille * 1.9 / 2 - taille * 1.4
        for index, (label, valeur) in enumerate(items):
            drawing.add(Rect(x_legende, y, taille * 0.95, taille * 0.95, fillColor=couleurs[index], strokeColor=None))
            texte_valeur = "%s  (%s)" % (Format_nombre(valeur, bloc.get("format") if bloc.get("format") != "entier" else "entier", self.o.symbole), Format_nombre(valeur / total * 100, "pourcent"))
            largeur_valeur = stringWidth(texte_valeur, self.o.police_gras, taille)
            texte_label = label
            while stringWidth(texte_label, self.o.police, taille) > largeur_legende - largeur_valeur - 30 and len(texte_label) > 4:
                texte_label = texte_label[:-2].rstrip() + "…"
            drawing.add(String(x_legende + taille * 1.5, y + 1, texte_label, fontName=self.o.police, fontSize=taille, fillColor=COULEUR_TEXTE))
            drawing.add(String(self.largeur, y + 1, texte_valeur, fontName=self.o.police_gras, fontSize=taille, fillColor=COULEUR_TEXTE_SECONDAIRE, textAnchor="end"))
            drawing.add(Line(x_legende, y - taille * 0.45, self.largeur, y - taille * 0.45, strokeColor=HexColor("#ECEAE3"), strokeWidth=0.5))
            y -= taille * 1.9
        return [KeepTogether([e for e in (self.Titre_graphique(bloc.get("titre")), drawing) if e])]


class Trait(Flowable):
    """ Trait horizontal sous les titres de rubriques """
    def __init__(self, largeur, couleur, epaisseur=1):
        Flowable.__init__(self)
        self.largeur, self.couleur, self.epaisseur = largeur, couleur, epaisseur

    def wrap(self, *args):
        return (self.largeur, self.epaisseur + 2)

    def draw(self):
        self.canv.setStrokeColor(self.couleur)
        self.canv.setLineWidth(self.epaisseur)
        self.canv.line(0, 1, self.largeur, 1)
