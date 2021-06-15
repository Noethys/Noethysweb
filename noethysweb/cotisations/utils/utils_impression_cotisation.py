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
        for IDcotisation, dictValeur in self.dict_donnees.items():
            if isinstance(IDcotisation, int):
                listeLabels.append((dictValeur["{FAMILLE_NOM}"], IDcotisation))
        listeLabels.sort()

        for labelDoc, IDcotisation in listeLabels:
            dictValeur = self.dict_donnees[IDcotisation]
            if dictValeur["select"] == True:
                self.story.append(DocAssign("ID", IDcotisation))
                nomSansCivilite = dictValeur["{FAMILLE_NOM}"]
                self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDcotisation)))

                # Saut de page
                self.story.append(PageBreak())



if __name__ == u"__main__":
    Impression()
