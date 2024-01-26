# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.utils import utils_dates, utils_impression, utils_preferences, utils_conversion
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        styleSheet = getSampleStyleSheet()
        h3 = styleSheet['Heading3']
        styleTexte = styleSheet['BodyText']
        styleTexte.fontName = "Helvetica"
        styleTexte.fontSize = 9
        styleTexte.borderPadding = 9
        styleTexte.leading = 12

        # ------------------- TITRE -----------------
        dataTableau = []
        largeursColonnes = [self.taille_cadre[2], ]
        dataTableau.append(("Reçu de règlement",))
        dataTableau.append(("",))
        style = TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (0, 0), "Helvetica-Bold", 19),
            ('FONT', (0, 1), (0, 1), "Helvetica", 8), ('LINEBELOW', (0, 0), (0, 0), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ])
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)
        self.story.append(Spacer(0, 10))

        # TEXTE D'INTRODUCTION
        paraStyleIntro = ParagraphStyle(name="intro", fontName="Helvetica", fontSize=11, leading=14, spaceBefore=0,
                                        spaceafter=0, leftIndent=0, rightIndent=0, alignment=0, )

        if self.dict_donnees["intro"]:
            texteIntro = self.dict_donnees["intro"]
            self.story.append(Paragraph(u"<i>%s</i>" % texteIntro, paraStyleIntro))
            self.story.append(Spacer(0, 20))

        couleurFond = (0.8, 0.8, 1)

        # ------------------- TABLEAU CONTENU -----------------

        dataTableau = []
        largeursColonnes = [120, self.taille_cadre[2]-120]

        paraStyle = ParagraphStyle(name="detail", fontName="Helvetica-Bold", fontSize=9)
        dataTableau.append(("Caractéristiques du règlement", ""))
        monnaie = utils_preferences.Get_monnaie()
        montantEnLettres = utils_conversion.trad(self.dict_donnees["{MONTANT_REGLEMENT}"]).strip()
        dataTableau.append(("Montant du règlement :", Paragraph(montantEnLettres.capitalize(), paraStyle)))
        dataTableau.append(("Mode de règlement :", Paragraph(self.dict_donnees["{MODE_REGLEMENT}"], paraStyle)))
        dataTableau.append(("Nom du payeur :", Paragraph(self.dict_donnees["{NOM_PAYEUR}"], paraStyle)))
        if self.dict_donnees["{NOM_EMETTEUR}"]:
            dataTableau.append(("Nom de l'émetteur :", Paragraph(self.dict_donnees["{NOM_EMETTEUR}"], paraStyle)))
        if self.dict_donnees["{NUM_PIECE}"]:
            dataTableau.append(("Numéro de pièce :", Paragraph(self.dict_donnees["{NUM_PIECE}"], paraStyle)))
        if self.dict_donnees["{DATE_DIFFERE}"]:
            dataTableau.append(("Encaissement différé :", Paragraph("A partir du %s" % self.dict_donnees["{DATE_DIFFERE}"], paraStyle)))

        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (0, -1), "Helvetica", 9),
            ('FONT', (1, 0), (1, -1), "Helvetica-Bold", 9),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONT', (0, 0), (0, 0), "Helvetica", 7), ('SPAN', (0, 0), (-1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), couleurFond),
        ])
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)

        # --------------------- LISTE DES PRESTATIONS ----------------
        prestations = self.dict_donnees["prestations"]
        if prestations:

            self.story.append(Spacer(0, 20))
            textePrestations = "En paiement des prestations suivantes :"
            self.story.append(Paragraph(u"<i>%s</i>" % textePrestations, paraStyleIntro))
            self.story.append(Spacer(0, 20))

            dataTableau = [("Date", "Activité", "Individu", "Intitulé", "Part utilisée")]
            largeur_temp = self.taille_cadre[2] - 50 - 50
            largeursColonnes = [50, largeur_temp/3+5, largeur_temp/3-10, largeur_temp/3+5, 50]

            paraStyle = ParagraphStyle(name="detail", fontName="Helvetica", fontSize=7, leading=7, spaceBefore=0, spaceAfter=0, )

            for prestation in prestations:
                date = utils_dates.ConvertDateToFR(prestation["prestation__date"])
                activite = prestation["prestation__activite__nom"] or ""
                individu = ("%s %s" % (prestation["prestation__individu__nom"], prestation["prestation__individu__prenom"] or "")) if prestation["prestation__individu__nom"] else ""
                label = prestation["prestation__label"]
                ventilation = prestation["total"]
                dataTableau.append((
                    Paragraph(u"<para align='center'>%s</para>" % date, paraStyle), Paragraph(activite, paraStyle),
                    Paragraph(individu, paraStyle), Paragraph(label, paraStyle),
                    Paragraph(u"<para align='right'>%.2f %s</para>" % (ventilation, utils_preferences.Get_symbole_monnaie()), paraStyle),))

            style = TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                ('TOPPADDING', (0, 1), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('FONT', (0, 0), (-1, 0), "Helvetica", 7),
                ('BACKGROUND', (0, 0), (-1, 0), couleurFond),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ])

            tableau = Table(dataTableau, largeursColonnes)
            tableau.setStyle(style)
            self.story.append(tableau)