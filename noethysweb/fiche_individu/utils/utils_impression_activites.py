# -*- coding: utf-8 -*-
#  Copyright (c) 2025 GIP RECIA.
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
        for IDactivite, dictValeur in self.dict_donnees.items():
            if isinstance(IDactivite, int):
                listeLabels.append((dictValeur["{ACTIVITE_NOM_LONG}"], IDactivite))
        listeLabels.sort()

        for labelDoc, IDactivite in listeLabels:
            dictValeur = self.dict_donnees[IDactivite]
            self.story.append(DocAssign("ID", IDactivite))
            nomSansCivilite = dictValeur["{ACTIVITE_NOM_LONG}"]
            self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDactivite)))

            # ----------- Insertion du cadre principal --------------
            if self.modele_doc is None:
                raise ValueError("Aucun modèle de document n'a été défini pour l'impression.")

            cadre_principal = self.modele_doc.FindObjet("cadre_principal")
            if cadre_principal is not None:
                # ------------------- TITRE -----------------
                dataTableau = []
                largeursColonnes = [self.taille_cadre[2], ]
                dataTableau.append(("Détails de l'Activité",))
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

                # ------------------- TABLEAU CONTENU -----------------
                dataTableau = []
                largeursColonnes = [120, self.taille_cadre[2] - 120]
                paraStyle = ParagraphStyle(name="detail", fontName="Helvetica-Bold", fontSize=9)

                dataTableau.append(("Nom de l'Activité", Paragraph(dictValeur["{ACTIVITE_NOM_LONG}"], paraStyle)))
                dataTableau.append(("Nom abrégé", Paragraph(dictValeur["{ACTIVITE_NOM_COURT}"], paraStyle)))
                dataTableau.append(
                    ("Nombre d'inscriptions", Paragraph(str(dictValeur["{NOMBRE_INSCRIPTIONS}"]), paraStyle)))
                dataTableau.append(("Familles inscrites", Paragraph(dictValeur["{FAMILLES}"], paraStyle)))

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
