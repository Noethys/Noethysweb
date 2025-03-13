# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.utils import utils_dates, utils_impression, utils_preferences
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import DocAssign, Flowable
from reportlab.lib import colors


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        styleSheet = getSampleStyleSheet()
        styleTexte = styleSheet['BodyText']
        styleTexte.fontName = "Helvetica"
        styleTexte.fontSize = 9
        styleTexte.borderPadding = 9
        styleTexte.leading = 12

        listeLabels = []
        for IDinscription, dictValeur in self.dict_donnees.items():
            if isinstance(IDinscription, int):
                listeLabels.append((dictValeur["{FAMILLE_NOM}"], IDinscription))
        listeLabels.sort()

        for labelDoc, IDinscription in listeLabels:
            dictValeur = self.dict_donnees[IDinscription]
            self.story.append(DocAssign("ID", IDinscription))
            nomSansCivilite = dictValeur["{FAMILLE_NOM}"]
            self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDinscription)))

            # ----------- Insertion du cadre principal --------------
            if self.modele_doc is None:
                raise ValueError("Aucun modèle de document n'a été défini pour l'impression.")

            cadre_principal = self.modele_doc.FindObjet("cadre_principal")
            if cadre_principal != None:

                # ------------------- TITRE -----------------
                dataTableau = []
                largeursColonnes = [self.taille_cadre[2], ]
                dataTableau.append(("Confirmation d'inscription",))
                dataTableau.append((u"",))
                style = TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 19),
                    ('FONT', (0, 1), (0, 1), "Helvetica", 8),
                    ('LINEBELOW', (0, 0), (0, 0), 0.25, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ])
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(style)
                self.story.append(tableau)
                self.story.append(Spacer(0, 10))

                # TEXTE D'INTRODUCTION
                # paraStyleIntro = ParagraphStyle(name="intro",
                #                                 fontName="Helvetica",
                #                                 fontSize=11,
                #                                 leading=14,
                #                                 spaceBefore=0,
                #                                 spaceafter=0,
                #                                 leftIndent=0,
                #                                 rightIndent=0,
                #                                 alignment=0,
                #                                 )
                #
                # if True:
                #     texteIntro = dictValeur["intro"]
                #     self.story.append(Paragraph(u"<i>%s</i>" % texteIntro, paraStyleIntro))
                #     self.story.append(Spacer(0, 20))

                # ------------------- TABLEAU CONTENU -----------------
                dataTableau = []
                largeursColonnes = [100, self.taille_cadre[2] - 100]
                paraStyle = ParagraphStyle(name="detail", fontName="Helvetica-Bold", fontSize=9)
                dataTableau.append(("Nom", Paragraph(dictValeur["{INDIVIDU_NOM}"], paraStyle)))
                dataTableau.append(("Prénom", Paragraph(dictValeur["{INDIVIDU_PRENOM}"] or "", paraStyle)))
                dataTableau.append(("Activité", Paragraph(dictValeur["{ACTIVITE_NOM_LONG}"], paraStyle)))
                dataTableau.append(("Groupe", Paragraph(dictValeur["{GROUPE_NOM_LONG}"], paraStyle)))
                dataTableau.append(("Catégorie", Paragraph(dictValeur["{NOM_CATEGORIE_TARIF}"], paraStyle)))
                dataTableau.append(("Date de début", Paragraph(dictValeur["{DATE_DEBUT}"], paraStyle)))
                dataTableau.append(("Date de fin", Paragraph(dictValeur["{DATE_FIN}"], paraStyle)))

                style = TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONT', (0, 0), (0, -1), "Helvetica", 9),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ])
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(style)
                self.story.append(tableau)

            # Saut de page
            self.story.append(PageBreak())



if __name__ == u"__main__":
    Impression()
