# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Depot, Reglement
from core.utils import utils_impression, utils_texte


class Impression(utils_impression.Impression):
    def Draw(self):
        # Importation du dépôt
        depot = Depot.objects.select_related("compte").get(pk=self.dict_donnees["iddepot"])

        # Recherche du tri de la liste
        tri_colonne = self.dict_donnees["tri_colonne"]
        if tri_colonne == "mode": tri = "mode__label"
        elif tri_colonne == "famille": tri = "famille__nom"
        elif tri_colonne == "payeur": tri = "payeur__nom"
        else: tri = tri_colonne
        if self.dict_donnees["tri_sens"] == "desc":
            tri = "-" + tri

        # Importation des règlements
        reglements = Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot).order_by(tri)

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_titre = ParagraphStyle(name="titre", fontName="Helvetica-bold", alignment=1, fontSize=11, spaceAfter=0, leading=11)

        # Création du titre du document
        self.Insert_header()

        # Tableau de description du dépôt
        dataTableau = [(
            Paragraph(depot.nom, style_titre),
            Paragraph("<br/>".join((
                "Date : %s" % depot.date.strftime("%d/%m/%Y") if depot.date else "---",
                "Compte : %s" % depot.compte.nom,
                "N° Compte : %s" % depot.compte.numero or "",
            )), style_defaut),
        )]
        tableau = Table(dataTableau, [320, 200])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        self.story.append(tableau)

        # Tableau des totaux du dépôt
        dataTableau = [(
            Paragraph("Total : <b>%s</b>" % utils_texte.Formate_montant(sum([reglement.montant for reglement in reglements])), style_centre),
            Paragraph("Quantité : <b>%s règlements</b>" % len(reglements), style_centre),
        )]
        tableau = Table(dataTableau, [260, 260])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
        ]))
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [("ID", "Date", "Mode", "Emetteur", "N° pièce", "Montant", "Famille", "Payeur", "N° quittancier", "Différé")]

        for reglement in reglements:
            ligne = []

            # ID
            ligne.append(reglement.pk)

            # Date
            ligne.append(Paragraph(reglement.date.strftime("%d/%m/%Y"), style_defaut))

            # Mode
            ligne.append(Paragraph(reglement.mode.label if reglement.mode else "", style_centre))

            # Emetteur
            ligne.append(Paragraph(reglement.emetteur.nom if reglement.emetteur else "", style_centre))

            # N° pièce
            ligne.append(Paragraph(reglement.numero_piece or "", style_centre))

            # Montant
            ligne.append(Paragraph(utils_texte.Formate_montant(reglement.montant), style_centre))

            # Famille
            ligne.append(Paragraph(reglement.famille.nom, style_centre))

            # Payeur
            ligne.append(Paragraph(reglement.payeur.nom if reglement.payeur else "", style_centre))

            # Numéro quittancier
            ligne.append(Paragraph(reglement.numero_quittancier or "", style_centre))

            # Différé
            ligne.append(Paragraph(reglement.date_differe.strftime("%d/%m/%Y") if reglement.date_differe else "", style_defaut))

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ])
        # Création du tableau
        tableau = Table(dataTableau, [30, 50, 50, 55, 45, 45, 85, 60, 50, 50], repeatRows=1)
        tableau.setStyle(style)
        self.story.append(tableau)
