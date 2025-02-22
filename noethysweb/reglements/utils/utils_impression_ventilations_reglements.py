# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Reglement, Ventilation
from core.utils import utils_impression, utils_texte


class Impression(utils_impression.Impression):
    def Draw(self):
        # Récupération des règlements
        if self.dict_donnees["type_selection"] == "DATE_SAISIE":
            conditions = Q(date__gte=self.dict_donnees["periode"][0]) & Q(date__lte=self.dict_donnees["periode"][1])
            description_document = "Les règlements saisis entre le %s et le %s" % (self.dict_donnees["periode"][0].strftime("%d/%m/%Y"), self.dict_donnees["periode"][1].strftime("%d/%m/%Y"))

        if self.dict_donnees["type_selection"] == "DATE_DEPOT":
            conditions = Q(depot__date__gte=self.dict_donnees["periode"][0]) & Q(depot__date__lte=self.dict_donnees["periode"][1])
            description_document = "Les règlements déposés entre le %s et le %s" % (self.dict_donnees["periode"][0].strftime("%d/%m/%Y"), self.dict_donnees["periode"][1].strftime("%d/%m/%Y"))

        if self.dict_donnees["type_selection"] == "FAMILLE":
            conditions = Q(famille=self.dict_donnees["famille"])
            description_document = "Les règlements de la famille %s" % self.dict_donnees["famille"].nom

            # Importation des règlements
        reglements = Reglement.objects.select_related("emetteur", "mode", "famille").filter(conditions).order_by("date")

        # Importation des ventilations
        ventilations = Ventilation.objects.select_related("reglement", "reglement__depot", "prestation", "prestation__activite", "prestation__individu", "prestation__cotisation").filter(reglement__in=reglements).order_by("prestation__date")
        dict_ventilations_reglement = {}
        for ventilation in ventilations:
            dict_ventilations_reglement.setdefault(ventilation.reglement, [])
            dict_ventilations_reglement[ventilation.reglement].append(ventilation)

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_droite = ParagraphStyle(name="right", fontName="Helvetica", alignment=2, fontSize=7, spaceAfter=0, leading=9)

        # Création du titre du document
        self.Insert_header()

        # Description du document
        self.story.append(Paragraph("<b>%s</b>" % description_document, style_centre))
        self.story.append(Spacer(0, 15))

        # Entête
        self.Insert_tableau(
            entetes=["Date", "Mode", "N° pièce", "Famille", "Montant", "Part utilisée"],
            largeurs=[50, 90, 50, 230, 50, 50],
            styles=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTRE")],
            lignes=[],
        )

        self.story.append(Spacer(0, 15))

        # Ligne du règlement
        for reglement in reglements:
            self.Insert_tableau(
                entetes=[],
                largeurs=[50, 90, 50, 230, 50, 50],
                styles=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
                    ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),],
                lignes=[(
                    Paragraph(reglement.date.strftime("%d/%m/%Y"), style_centre),
                    Paragraph(reglement.mode.label, style_centre),
                    Paragraph(reglement.numero_piece or "", style_centre),
                    Paragraph(reglement.famille.nom, style_centre),
                    Paragraph("<b>%s</b>" % utils_texte.Formate_montant(reglement.montant), style_centre),
                    Paragraph(utils_texte.Formate_montant(sum([v.montant for v in dict_ventilations_reglement.get(reglement, [])])), style_droite),
                )],
            )

            # Lignes des prestations
            self.Insert_tableau(
                entetes=["Date", "Activité", "Individu", "Label de la prestation", "Part utilisée"],
                largeurs=[50, 140, 120, 160, 50],
                styles=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONT", (0, 0), (-1, -1), "Helvetica", 5),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTRE")],
                lignes=[],
            )

            for ventilation in dict_ventilations_reglement.get(reglement, []):
                self.Insert_tableau(
                    entetes=[],
                    largeurs=[50, 140, 120, 160, 50],
                    styles=[
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "CENTRE")],
                    lignes=[(
                        Paragraph(ventilation.prestation.date.strftime("%d/%m/%Y"), style_centre),
                        Paragraph(ventilation.prestation.activite.nom if ventilation.prestation.activite else "", style_defaut),
                        Paragraph(ventilation.prestation.individu.Get_nom() if ventilation.prestation.individu else "", style_defaut),
                        Paragraph(ventilation.prestation.label, style_defaut),
                        Paragraph(utils_texte.Formate_montant(ventilation.montant), style_droite),
                    )],
                )

            self.story.append(Spacer(0, 15))

    def Insert_tableau(self, entetes=[], largeurs=[], styles=[], lignes=[]):
        if entetes:
            lignes.insert(0, entetes)
        tableau = Table(lignes, largeurs, repeatRows=0)
        tableau.setStyle(TableStyle(styles))
        self.story.append(tableau)
