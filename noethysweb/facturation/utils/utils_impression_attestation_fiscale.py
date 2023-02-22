# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.utils import utils_dates, utils_impression, utils_preferences
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import DocAssign, Flowable


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
            self.story.append(DocAssign("ID", IDfamille))
            nomSansCivilite = dictValeur["nomSansCivilite"]
            self.story.append(utils_impression.Bookmark(nomSansCivilite, str(IDfamille)))

            # ------------------- TITRE -----------------

            if self.dict_options["afficher_titre"]:
                dataTableau = []
                largeursColonnes = [self.taille_cadre[2],]
                dataTableau.append((self.dict_options["texte_titre"],))
                dataTableau.append(("Période du %s au %s" % (dictValeur["{DATE_DEBUT}"], dictValeur["{DATE_FIN}"]),))
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

            # INTRO
            if self.dict_options["texte_introduction"]:
                listeParagraphes = dictValeur["texte_introduction"].split("</para>")
                for paragraphe in listeParagraphes:
                    textePara = Paragraph("%s" % paragraphe, paraStyle)
                    self.story.append(textePara)
                self.story.append(Spacer(0, 25))

            # DETAIL par enfant
            dataTableau = [("Nom et prénom", "Date de naissance", "Montant")]
            largeursColonnes = [220, 80, 80]

            for dict_individu in dictValeur["individus"]:
                dataTableau.append((
                    dict_individu["individu"].Get_nom(),
                    utils_dates.ConvertDateToFR(dict_individu["individu"].date_naiss),
                    "%.2f %s" % (dict_individu["montant"], utils_preferences.Get_symbole_monnaie())
                ))

            dataTableau.append(("", "Total :", dictValeur["{TOTAL}"]))

            style = TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -2), 0.25, colors.black), ('FONT', (0, 0), (-1, 0), "Helvetica", 6),
                ('FONT', (0, 1), (-1, -1), "Helvetica", 10), ('TOPPADDING', (0, 1), (-1, -2), 10), ('BOTTOMPADDING', (0, 1), (-1, -2), 10),
                ('GRID', (-1, -1), (-1, -1), 0.25, colors.black), ('FONT', (-1, -1), (-1, -1), "Helvetica-Bold", 10),
                ('ALIGN', (-2, -1), (-2, -1), 'RIGHT'), ('FONT', (-2, -1), (-2, -1), "Helvetica", 6), ])
            tableau = Table(dataTableau, largeursColonnes)
            tableau.setStyle(style)
            self.story.append(tableau)

            # Saut de page
            self.story.append(PageBreak())
