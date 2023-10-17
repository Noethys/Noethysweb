# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import DocAssign
from core.utils import utils_dates, utils_impression, utils_texte


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):

        # ----------- Insertion du contenu des frames --------------
        listeNomsSansCivilite = []
        for IDfamille, dictValeur in self.dict_donnees.items():
            if isinstance(dictValeur, dict):
                listeNomsSansCivilite.append((dictValeur["nomSansCivilite"], IDfamille))
        listeNomsSansCivilite.sort()

        for nomSansCivilite, IDfamille in listeNomsSansCivilite:
            dictValeur = self.dict_donnees[IDfamille]
            if dictValeur["select"] == True:

                self.story.append(DocAssign("ID", IDfamille))
                nomSansCivilite = dictValeur["nomSansCivilite"]
                self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDfamille)))

                # ------------------- TITRE -----------------
                dataTableau = []
                largeursColonnes = [self.taille_cadre[2], ]
                dataTableau.append((dictValeur["titre"],))
                dataTableau.append(("Situation au %s" % utils_dates.ConvertDateENGtoFR(dictValeur["date_reference"]),))
                style = TableStyle(
                    [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 19),
                        ('FONT', (0, 1), (0, 1), "Helvetica", 8), ('LINEBELOW', (0, 0), (0, 0), 0.25, colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ])
                tableau = Table(dataTableau, largeursColonnes)
                tableau.setStyle(style)
                self.story.append(tableau)
                self.story.append(Spacer(0, 30))

                paraStyle = ParagraphStyle(name="contenu", fontName="Helvetica", fontSize=11, spaceBefore=0,
                                           spaceafter=0, leftIndent=6, rightIndent=6)

                # Conversion html en str si nécessaire
                texte = dictValeur["texte"].replace("<br>", "\n\n")
                texte = texte.replace("&nbsp;", " ")
                texte = utils_texte.Textify(texte)

                for ligne in texte.splitlines():
                    if ligne == "":
                        ligne = "&nbsp;"
                    self.story.append(Paragraph("<para>%s</para>" % ligne, paraStyle))

                # Saut de page
                self.story.append(PageBreak())


if __name__ == u"__main__":
    Impression()
