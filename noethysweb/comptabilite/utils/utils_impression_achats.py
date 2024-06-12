# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.db.models import Q
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import AchatArticle
from core.utils import utils_dates, utils_impression


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        kwds["taille_page"] = landscape(A4) if kwds["dict_donnees"]["orientation"] == "paysage" else portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation des articles
        conditions = Q(
            fournisseur__in=self.dict_donnees["fournisseurs"],
            demande__date_echeance__gte=self.dict_donnees["periode"][0],
            demande__date_echeance__lte=self.dict_donnees["periode"][1],
            achete__in=self.dict_donnees["achete"]
        )
        articles = AchatArticle.objects.select_related("fournisseur", "categorie", "demande", "demande__collaborateur").filter(conditions).order_by("demande__iddemande")
        if not articles:
            self.erreurs.append("Aucun article n'a été trouvé avec les paramètres donnés")

        # Préparation des polices
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)

        # Création du titre du document
        self.Insert_header()

        # Préparation du tableau
        largeur_contenu = self.taille_page[0] - 75

        def Insert_barre_titre(label="", styles=[]):
            tableau = Table([[label]], [largeur_contenu])
            tableau.setStyle(TableStyle(styles))
            self.story.append(tableau)

        dict_resultats = {}
        for article in articles:
            dict_resultats.setdefault(article.fournisseur, {})
            dict_resultats[article.fournisseur].setdefault(article.categorie, [])
            dict_resultats[article.fournisseur][article.categorie].append(article)

        for fournisseur, categories in dict_resultats.items():

            # Nom du fournisseur
            Insert_barre_titre(label=fournisseur.nom, styles=[
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, -1), "Helvetica-Bold", 8),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('ALIGN', (0, 0), (-1, -1), "CENTRE"),
                ('TEXTCOLOR', (0, 0), (-1, -1), (1, 1, 1)), ('BACKGROUND', (0, 0), (-1, -1), (0.5, 0.5, 0.5)),
            ])

            # Calcul des largeurs des colonnes
            largeur_grande_colonne = (largeur_contenu - 100) / 5
            largeurs_colonnes = [20, largeur_grande_colonne, 30, largeur_grande_colonne, 50, largeur_grande_colonne, largeur_grande_colonne, largeur_grande_colonne]

            # Entêtes de colonnes
            tableau = Table([("Acheté", "Article", "Quantité", "Observations article", "Echéance", "Libellé demande", "Collaborateur", "Observations demande")], largeurs_colonnes)
            tableau.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, -1), "Helvetica", 5),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('ALIGN', (0, 0), (-1, -1), 'CENTRE'), ]))
            self.story.append(tableau)

            # Articles
            liste_key_categorie = sorted(list(categories.keys()), key=lambda x: x.ordre)
            for categorie in liste_key_categorie:

                # Nom de la catégorie
                Insert_barre_titre(label=categorie.nom, styles=[
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, -1), "Helvetica-Bold", 7),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('ALIGN', (0, 0), (-1, -1), "LEFT"),
                    ('TEXTCOLOR', (0, 0), (-1, -1), (0, 0, 0)), ('BACKGROUND', (0, 0), (-1, -1), (0.8, 0.8, 0.8)),
                ])

                # Articles
                dataTableau = []
                for article in categories[categorie]:
                    ligne = [
                        Paragraph("X" if article.achete else "", style_centre),
                        Paragraph(article.libelle, style_centre),
                        Paragraph(article.quantite or "", style_centre),
                        Paragraph(article.observations, style_centre),
                        Paragraph(utils_dates.ConvertDateToFR(article.demande.date_echeance), style_centre),
                        Paragraph(article.demande.libelle, style_centre),
                        Paragraph(article.demande.collaborateur.prenom if article.demande.collaborateur else "", style_centre),
                        Paragraph(article.demande.observations, style_centre),
                    ]
                    dataTableau.append(ligne)

                tableau = Table(dataTableau, largeurs_colonnes)
                style = TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black), ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),])
                tableau.setStyle(style)
                self.story.append(tableau)

            # Saut de page après fournisseur
            self.story.append(Spacer(0, 20))
