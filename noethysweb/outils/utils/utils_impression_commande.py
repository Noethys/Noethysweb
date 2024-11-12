# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import Commande, CommandeModeleColonne
from core.utils import utils_dates, utils_impression


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        kwds["taille_page"] = landscape(A4) if kwds["dict_donnees"]["options_impression"]["orientation"] == "paysage" else portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        commande = Commande.objects.select_related("modele").get(pk=self.dict_donnees["idcommande"])
        colonnes = CommandeModeleColonne.objects.filter(modele=commande.modele).order_by("ordre")

        largeurContenu = self.taille_page[0] - 75

        # Création du titre du document
        self.Insert_header()

        # Insère le nom et la période de la commande
        style_titre_commande = ParagraphStyle(name="1", alignment=1, fontName="Helvetica-Bold", fontSize=9, leading=8, spaceAfter=14)
        self.story.append(Paragraph("<para>%s - Du %s au %s</para>" % (commande.nom, commande.date_debut.strftime("%d/%m/%Y"), commande.date_fin.strftime("%d/%m/%Y")), style_titre_commande))

        # Styles
        style_entete = ParagraphStyle(name="1", alignment=1, fontName="Helvetica-Bold", fontSize=7, leading=8, spaceAfter=2)
        style_numerique = ParagraphStyle(name="2", alignment=2, fontName="Helvetica", fontSize=7, leading=8, spaceAfter=2)
        style_total = ParagraphStyle(name="3", alignment=2, fontName="Helvetica-Bold", fontSize=7, leading=8, spaceAfter=2)
        style_texte = ParagraphStyle(name="4", alignment=0, fontName="Helvetica", fontSize=7, leading=8, spaceAfter=2)

        # Calcule des largeurs de colonne
        largeur_colonne_date = 110

        def Get_largeur_colonne(colonne):
            return 40 if "NUMERIQUE" in colonne.categorie else 100

        total_largeurs_colonnes = sum([Get_largeur_colonne(colonne) for colonne in colonnes])
        dict_largeurs = {colonne.pk: 1.0 * Get_largeur_colonne(colonne) / total_largeurs_colonnes * (largeurContenu - largeur_colonne_date) for colonne in colonnes}

        # Dessin du tableau de données
        dataTableau = []
        largeurs_colonnes = [largeur_colonne_date,]

        # Dessin des noms de colonnes
        ligne = [Paragraph("Date", style_entete),]
        for colonne in colonnes:
            ligne.append(Paragraph(colonne.nom, style_entete))
            largeurs_colonnes.append(dict_largeurs[colonne.pk])
        dataTableau.append(ligne)

        # Récupération des dates
        liste_dates = list({utils_dates.ConvertDateENGtoDate(case["date"]): True for key, case in self.dict_donnees["cases"].items() if case["date"]}.keys())
        liste_dates.sort()

        # Filtrage des dates selon les options d'impression
        options_impression = self.dict_donnees["options_impression"]
        if options_impression["selection_dates"] == "AUJOURDHUI":
            selection_dates = (datetime.date.today(), datetime.date.today())
        elif options_impression["selection_dates"] == "DEMAIN":
            selection_dates = (datetime.date.today() + datetime.timedelta(days=1), datetime.date.today() + datetime.timedelta(days=1))
        elif options_impression["selection_dates"] == "SELECTION":
            selection_dates = utils_dates.ConvertDateRangePicker(options_impression["periode"])
        else:
            selection_dates = None

        # Dessin des lignes
        dict_totaux_colonnes = {}
        for date in liste_dates:
            if not selection_dates or (selection_dates[0] <= date <= selection_dates[1]):
                ligne = [utils_dates.DateComplete(date)]
                for colonne in colonnes:
                    key_case = "%s_%d" % (date, colonne.pk)
                    if "NUMERIQUE" in colonne.categorie:
                        valeur = str(self.dict_donnees["cases"][key_case]["valeur"])
                        style = style_total if "TOTAL" in colonne.categorie else style_numerique
                        dict_totaux_colonnes.setdefault(colonne.pk, 0)
                        dict_totaux_colonnes[colonne.pk] += int(valeur)
                    else:
                        valeur = self.dict_donnees["cases"][key_case]["texte"]
                        valeur = valeur.replace("\n", "<br/>")
                        style = style_texte
                    ligne.append(Paragraph(valeur, style))
                dataTableau.append(ligne)

        # Ajout de la ligne de total
        dataTableau.append(["Total"] + [Paragraph(str(dict_totaux_colonnes.get(colonne.pk, "")), style_total) for colonne in colonnes ])

        listeStyles = [
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONT',(0,0),(-1,-1), "Helvetica", 7),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('ALIGN', (0,1), (-2,-1), 'CENTER'),
                ('FONT', (0, 0), (0, -1), "Helvetica-Bold", 7),
                ('FONT', (0, 0), (-1, 0), "Helvetica-Bold", 7),
                ]

        # Création du tableau
        tableau = Table(dataTableau, largeurs_colonnes, repeatRows=1)
        tableau.setStyle(TableStyle(listeStyles))
        self.story.append(tableau)

        # Observations
        if commande.observations:
            style_observations = ParagraphStyle(name="2", alignment=1, fontName="Helvetica", fontSize=7, leading=8, spaceBefore=10)
            self.story.append(Paragraph(commande.observations, style=style_observations))

        # Mémorisation des champs de fusion
        self.dict_donnees["champs"] = {
            "{NOM_COMMANDE}": commande.nom,
            "{DATE_DEBUT}": commande.date_debut.strftime("%d/%m/%Y"),
            "{DATE_FIN}": commande.date_fin.strftime("%d/%m/%Y"),
        }
