# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import datetime
from core.utils import utils_dates, utils_modeles_documents, utils_preferences, utils_fichiers
from core.models import Organisateur
from core.data import data_modeles_emails
from django.core.cache import cache
from django.conf import settings
from uuid import uuid4

from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, NextPageTemplate
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import ParagraphAndImage, Image
from reportlab.platypus.frames import Frame
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.barcode import code39, qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.platypus.flowables import DocAssign, Flowable


def Get_motscles_defaut(request=None):
    organisateur = cache.get('organisateur', None)
    if not organisateur:
        organisateur = cache.get_or_set('organisateur', Organisateur.objects.filter(pk=1).first())

    dict_valeurs = {
        "{ORGANISATEUR_NOM}": organisateur.nom,
        "{ORGANISATEUR_RUE}": organisateur.rue,
        "{ORGANISATEUR_CP}": organisateur.cp,
        "{ORGANISATEUR_VILLE}": organisateur.ville,
        "{ORGANISATEUR_TEL}": organisateur.tel,
        "{ORGANISATEUR_FAX}": organisateur.fax,
        "{ORGANISATEUR_MAIL}": organisateur.mail,
        "{ORGANISATEUR_SITE}": organisateur.site,
        "{ORGANISATEUR_AGREMENT}": organisateur.num_agrement,
        "{ORGANISATEUR_SIRET}": organisateur.num_siret,
        "{ORGANISATEUR_APE}": organisateur.code_ape,
        "{UTILISATEUR_NOM_COMPLET}": request.user.get_full_name() if request else "",
        "{UTILISATEUR_NOM}": request.user.last_name if request else "",
        "{UTILISATEUR_PRENOM}": request.user.first_name if request else "",
        "{DATE_LONGUE}": utils_dates.DateComplete(datetime.date.today()),
        "{DATE_COURTE}": utils_dates.ConvertDateToFR(datetime.date.today()),
    }
    return dict_valeurs


def Template(canvas, doc):
    """ Première page """
    doc.modele_doc.DessineFond(canvas, doc.dict_donnees)
    doc.modele_doc.DessineFormes(canvas)


class MyPageTemplate(PageTemplate):
    def __init__(self, id=-1, pageSize=None, doc=None):
        self.pageWidth = pageSize[0]
        self.pageHeight = pageSize[1]

        # Récupère les coordonnées du cadre principal
        x, y, l, h = doc.taille_cadre
        frame1 = Frame(x, y, l, h, id='F1', leftPadding=0, topPadding=0, rightPadding=0, bottomPadding=0)
        PageTemplate.__init__(self, id, [frame1], Template)

    def afterDrawPage(self, canvas, doc):
        # Récupération des valeurs
        ID = doc._nameSpace.get("ID")
        dict_valeurs = doc.dict_donnees.get(ID, {})
        if not ID:
            dict_valeurs = doc.dict_donnees

        # Dessin du coupon-réponse vertical
        coupon_vertical = doc.modele_doc.FindObjet("coupon_vertical")
        if doc.dict_options.get("afficher_coupon_reponse") and coupon_vertical:
            x, y, largeur, hauteur = doc.modele_doc.GetCoordsObjet(coupon_vertical)
            canvas.saveState()
            # Ciseaux
            # canvas.drawImage(Chemins.GetStaticPath("Images/Special/Ciseaux.png"), x + 1 * mm, y + hauteur - 5 * mm, 0.5 * cm, 1 * cm, preserveAspectRatio=True)
            # Rectangle
            canvas.setDash(3, 3)
            canvas.setLineWidth(0.25)
            canvas.setStrokeColorRGB(0, 0, 0)
            canvas.rect(x, y, largeur, hauteur, fill=0)
            # Textes
            canvas.rotate(90)
            canvas.setFont("Helvetica", 8)
            canvas.drawString(y + 2 * mm, -x - 4 * mm, "Merci de joindre ce coupon à votre règlement")
            canvas.setFont("Helvetica", 7)
            if "total" in dict_valeurs:
                solde = dict_valeurs["total"] - dict_valeurs["ventilation"]
                if doc.dict_options["integrer_impayes"] == True:
                    solde += dict_valeurs["total_reports"]
            if "solde_num" in dict_valeurs:
                solde = dict_valeurs["solde_num"]
            numero = dict_valeurs["numero"]
            nom = dict_valeurs["nomSansCivilite"]
            canvas.drawString(y + 2 * mm, -x - 9 * mm, "%s - %.02f %s" % (numero, solde, utils_preferences.Get_symbole_monnaie()))
            canvas.drawString(y + 2 * mm, -x - 12 * mm, "%s" % nom)
            # Code-barres
            if doc.dict_options["afficher_codes_barres"] == True and "{CODEBARRES_NUM_FACTURE}" in dict_valeurs:
                barcode = code39.Extended39(dict_valeurs["{CODEBARRES_NUM_FACTURE}"], humanReadable=False)
                barcode.drawOn(canvas, y + 36 * mm, -x - 13 * mm)
            if doc.dict_options["afficher_codes_barres"] == True and "{CODEBARRES_NUM_RAPPEL}" in dict_valeurs:
                barcode = code39.Extended39(dict_valeurs["{CODEBARRES_NUM_RAPPEL}"], humanReadable=False)
                barcode.drawOn(canvas, y + 36 * mm, -x - 13 * mm)
            canvas.restoreState()

        # Dessin du coupon-réponse horizontal
        coupon_horizontal = doc.modele_doc.FindObjet("coupon_horizontal")
        if doc.dict_options.get("afficher_coupon_reponse") and coupon_horizontal:
            x, y, largeur, hauteur = doc.modele_doc.GetCoordsObjet(coupon_horizontal)
            canvas.saveState()
            # Rectangle
            canvas.setDash(3, 3)
            canvas.setLineWidth(0.25)
            canvas.setStrokeColorRGB(0, 0, 0)
            canvas.rect(x, y, largeur, hauteur, fill=0)
            # Textes
            canvas.setFont("Helvetica", 8)
            canvas.drawString(x + 2 * mm, y + hauteur - 4 * mm, "Merci de joindre ce coupon à votre règlement")
            canvas.setFont("Helvetica", 7)
            if "total" in dict_valeurs:
                solde = dict_valeurs["total"] - dict_valeurs["ventilation"]
                if doc.dict_options["integrer_impayes"] == True:
                    solde += dict_valeurs["total_reports"]
            if "solde_num" in dict_valeurs:
                solde = dict_valeurs["solde_num"]
            numero = dict_valeurs["numero"]
            nom = dict_valeurs["nomSansCivilite"]
            canvas.drawString(x + 2 * mm, y + hauteur - 9 * mm, "%s - %.02f %s" % (numero, solde, utils_preferences.Get_symbole_monnaie()))
            canvas.drawString(x + 2 * mm, y + hauteur - 12 * mm, "%s" % nom)
            # Code-barres
            if doc.dict_options["afficher_codes_barres"] == True and "{CODEBARRES_NUM_FACTURE}" in dict_valeurs:
                barcode = code39.Extended39(dict_valeurs["{CODEBARRES_NUM_FACTURE}"], humanReadable=False)
                barcode.drawOn(canvas, x + 36 * mm, y + hauteur - 13 * mm)
            if doc.dict_options["afficher_codes_barres"] == True and "{CODEBARRES_NUM_RAPPEL}" in dict_valeurs:
                barcode = code39.Extended39(dict_valeurs["{CODEBARRES_NUM_RAPPEL}"], humanReadable=False)
                barcode.drawOn(canvas, x + 36 * mm, y + hauteur - 13 * mm)
            # Ciseaux
            # canvas.rotate(-90)
            # canvas.drawImage(Chemins.GetStaticPath("Images/Special/Ciseaux.png"), -y - hauteur + 1 * mm, x + largeur - 5 * mm, 0.5 * cm, 1 * cm, preserveAspectRatio=True)
            canvas.restoreState()

        canvas.saveState()

        # Insertion des codes-barres
        if doc.dict_options.get("afficher_codes_barres"):
            doc.modele_doc.DessineCodesBarres(canvas, dict_valeurs=dict_valeurs)

        # Insertion des lignes de textes
        doc.modele_doc.DessineImages(canvas, dict_valeurs=dict_valeurs)
        doc.modele_doc.DessineTextes(canvas, dict_valeurs=dict_valeurs)

        canvas.restoreState()


class Bookmark(Flowable):
    def __init__(self, title, key):
        self.title = title
        self.key = key
        Flowable.__init__(self)

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        self.canv.showOutline()
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, 0, 0)



class Impression():
    def __init__(self, titre="", dict_donnees={}, dict_options={}, IDmodele=None, taille_page=None, generation_auto=True, request=None):
        self.titre = titre
        self.IDmodele = IDmodele
        self.dict_options = dict_options
        self.taille_page = taille_page
        self.modele_doc = None
        self.request = request
        if generation_auto:
            self.Generation_document(dict_donnees=dict_donnees)

    def Generation_document(self, dict_donnees={}):
        self.dict_donnees = dict_donnees
        self.erreurs = []

        # Rajoute les mots-clés par défaut au dict_donnees
        motscles_defaut = Get_motscles_defaut(request=self.request)
        self.dict_donnees.update(motscles_defaut)
        for key, valeurs in self.dict_donnees.items():
            if isinstance(key, int):
                self.dict_donnees[key].update(motscles_defaut)

        # Créé le répertoire temp s'il n'existe pas
        rep_temp = utils_fichiers.GetTempRep()

        # Initialisation du document
        self.nom_fichier = "/temp/%s.pdf" % uuid4()
        self.chemin_fichier = settings.MEDIA_ROOT + self.nom_fichier

        if self.IDmodele:

            # Importation du modèle de document
            if not self.modele_doc:
                logger.debug("Initialisation du modele_doc...")
                self.modele_doc = utils_modeles_documents.Modele_doc(IDmodele=self.IDmodele)
            self.taille_page = utils_modeles_documents.ConvertTailleModeleEnPx((self.modele_doc.modele.largeur, self.modele_doc.modele.hauteur))

            self.doc = BaseDocTemplate(self.chemin_fichier, pagesize=self.taille_page, showBoundary=False)
            self.doc.modele_doc = self.modele_doc
            self.doc.dict_donnees = self.dict_donnees
            self.doc.dict_options = self.dict_options

            # Vérifie qu'un cadre principal existe bien dans le document
            cadre_principal = self.modele_doc.FindObjet("cadre_principal")
            if cadre_principal:
                self.taille_cadre = self.doc.taille_cadre = self.modele_doc.GetCoordsObjet(cadre_principal)
            else:
                self.taille_cadre = self.doc.taille_cadre = (0, 0, self.taille_page[0], self.taille_page[1])

            # Ajoute le template au document
            self.doc.addPageTemplates(MyPageTemplate(pageSize=self.taille_page, doc=self.doc))

        else:
            if not self.taille_page: self.taille_page = A4
            self.doc = SimpleDocTemplate(self.chemin_fichier, topMargin=30, bottomMargin=30, pagesize=self.taille_page, showBoundary=False)

        # Prépare la story
        self.story = []

        # Dessine le doc
        self.Draw()

        # Finalise le doc
        self.doc.build(self.story)

    def Draw(self):
        pass

    def Insert_header(self, titre=None, espace_apres=20, detail=None):
        """ Création d'un header standard """
        # Importation de l'organisateur
        organisateur = cache.get('organisateur', None)
        if not organisateur:
            organisateur = cache.get_or_set('organisateur', Organisateur.objects.filter(pk=1).first())

        # Dessin du tableau
        dataTableau = []
        largeursColonnes = ((self.taille_page[0] - 175, 100))
        details = "%s\n%s" % (organisateur.nom, datetime.datetime.now().strftime("%d/%m/%Y-%H:%M"))
        if detail:
            details += "\n%s" % detail
        dataTableau.append((titre or self.titre, details))
        style = TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 16),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('FONT', (1, 0), (1, 0), "Helvetica", 6), ])
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)
        self.story.append(Spacer(0, espace_apres))

    def Get_champs_fusion(self):
        return self.dict_donnees

    def Get_champs_fusion_pour_email(self, categorie="", key=None):
        """ Renvoie uniquement les champs de fusion destinés à l'envoi par email """
        liste_mots_cles = data_modeles_emails.Get_mots_cles(categorie)
        dict_resultats = {}
        for motcle, exemple in liste_mots_cles:
            dict_resultats[motcle] = self.dict_donnees[key].get(motcle, "")
        return dict_resultats

    def Get_nom_fichier(self):
        return self.nom_fichier

