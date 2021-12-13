# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.utils import utils_dates, utils_impression
from reportlab.platypus import Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.flowables import Image, DocAssign
from reportlab.platypus.frames import Frame
from reportlab.lib import colors
from core.models import Activite, Individu
from django.db.models import Q
from django.conf import settings

LARGEUR_COLONNE = 158


def Template(canvas, doc):
    """ Première page de l'attestation """
    canvas.saveState()
    # Insertion de l'image de fond de page
    canvas.drawImage(settings.STATIC_ROOT + "/images/%s.jpg" % doc.theme, 0, 0, doc.pagesize[0], doc.pagesize[1], preserveAspectRatio=True)
    canvas.restoreState()


class MyPageTemplate(PageTemplate):
    def __init__(self, id=-1, pageSize=None, doc=None):
        self.pageWidth = pageSize[0]
        self.pageHeight = pageSize[1]

        self.hauteurColonne = 700
        self.margeBord = 40
        self.margeInter = 20

        x, y, l, h = (self.margeBord, self.margeBord, LARGEUR_COLONNE, self.hauteurColonne)
        frame1 = Frame(x, y, l, h, id='F1', leftPadding=0, topPadding=0, rightPadding=0, bottomPadding=0)

        x, y, l, h = (self.margeBord + LARGEUR_COLONNE + self.margeInter, self.margeBord, LARGEUR_COLONNE, self.hauteurColonne)
        frame2 = Frame(x, y, l, h, id='F2', leftPadding=0, topPadding=0, rightPadding=0, bottomPadding=0)

        x, y, l, h = (self.margeBord + (LARGEUR_COLONNE + self.margeInter) * 2, self.margeBord, LARGEUR_COLONNE, self.hauteurColonne)
        frame3 = Frame(x, y, l, h, id='F2', leftPadding=0, topPadding=0, rightPadding=0, bottomPadding=0)

        PageTemplate.__init__(self, id, [frame1, frame2, frame3], Template)

    def afterDrawPage(self, canvas, doc):
        numMois = doc._nameSpace["numMois"]
        nomMois = utils_dates.LISTE_MOIS[numMois - 1].capitalize()

        # Affiche le nom du mois en haut de la page
        canvas.saveState()

        canvas.setLineWidth(0.25)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.setFillColorRGB(0.7, 0.7, 1)
        canvas.rect(self.margeBord, self.pageHeight - self.margeBord, self.pageWidth - (self.margeBord * 2), -38, fill=1)

        canvas.setFont("Helvetica-Bold", 24)
        canvas.setFillColorRGB(0, 0, 0)
        canvas.drawString(self.margeBord + 10, self.pageHeight - self.margeBord - 26, nomMois)

        canvas.restoreState()


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Initialisation du document
        self.doc = BaseDocTemplate(self.chemin_fichier, pagesize=self.taille_page, showBoundary=False)
        self.doc.theme = self.dict_donnees["theme"]
        self.doc.addPageTemplates(MyPageTemplate(pageSize=self.taille_page, doc=self.doc))

        # Récupération des paramètres
        param_activites = self.dict_donnees["activites"]
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        conditions = Q(inscription__activite__in=liste_activites)
        if self.dict_donnees["presents"]:
            conditions &= Q(inscription__consommation__date__gte=self.dict_donnees["presents"][0], inscription__consommation__date__lte=self.dict_donnees["presents"][1])
        individus = Individu.objects.filter(conditions).distinct()

        if not individus:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        dictAnniversaires = {}
        for individu in individus:
            if individu.date_naiss:
                jour = individu.date_naiss.day
                mois = individu.date_naiss.month

                # Mémorisation du IDindividu
                dictAnniversaires.setdefault(mois, {})
                dictAnniversaires[mois].setdefault(jour, [])
                dictAnniversaires[mois][jour].append(individu)

        # ---------------- Création du PDF -------------------

        # Mois
        listeMois = list(dictAnniversaires.keys())
        listeMois.sort()
        for numMois in listeMois:

            # Mémorise le numéro de mois pour le titre de la page
            self.story.append(DocAssign("numMois", numMois))

            # Jours
            dictJours = dictAnniversaires[numMois]
            listeJours = list(dictJours.keys())
            listeJours.sort()
            for numJour in listeJours:
                dataTableau = []
                largeursColonnes = []

                # Recherche des entêtes de colonnes
                if self.dict_donnees["afficher_photos"]:
                    largeursColonnes.append(self.dict_donnees["afficher_photos"] + 6)

                # Colonne nom de l'individu
                largeursColonnes.append(LARGEUR_COLONNE - sum(largeursColonnes))

                # Label numéro de jour
                ligne = [str(numJour),]
                if self.dict_donnees["afficher_photos"]:
                    ligne.append("")
                dataTableau.append(ligne)

                # Individus
                for individu in dictAnniversaires[numMois][numJour]:
                    ligne = []

                    # Photo
                    if self.dict_donnees["afficher_photos"]:
                        nom_fichier = individu.Get_photo(forTemplate=False)
                        if "media/" in nom_fichier:
                            nom_fichier = settings.MEDIA_ROOT + nom_fichier.replace("media/", "")
                        img = Image(nom_fichier, width=self.dict_donnees["afficher_photos"], height=self.dict_donnees["afficher_photos"])
                        ligne.append(img)

                    # Nom
                    ligne.append("%s %s" % (individu.nom, individu.prenom))

                    # Ajout de la ligne individuelle
                    dataTableau.append(ligne)

                couleurFondJour = (0.8, 0.8, 1)
                couleurFondTableau = (1, 1, 1)

                style = TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), couleurFondTableau),

                    ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('ALIGN', (0, 1), (-1, -1), 'CENTRE'),

                    ('SPAN', (0, 0), (-1, 0)),
                    ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 10),
                    ('BACKGROUND', (0, 0), (-1, 0), couleurFondJour),
                ])

                # Création du tableau
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(style)
                self.story.append(tableau)
                self.story.append(Spacer(0, 10))

            # Saut de page après un mois
            self.story.append(PageBreak())
