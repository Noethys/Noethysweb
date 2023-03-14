# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.utils import utils_impression
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak
from reportlab.platypus.flowables import DocAssign


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
        for IDlocation, dictValeur in self.dict_donnees.items():
            if isinstance(IDlocation, int):
                listeLabels.append((dictValeur["{FAMILLE_NOM}"], IDlocation))
        listeLabels.sort()

        for labelDoc, IDlocation in listeLabels:
            dictValeur = self.dict_donnees[IDlocation]
            if dictValeur["select"] == True:
                self.story.append(DocAssign("ID", IDlocation))
                nomSansCivilite = dictValeur["{FAMILLE_NOM}"]
                self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDlocation)))

                # Saut de page
                self.story.append(PageBreak())


if __name__ == u"__main__":
    Impression()
