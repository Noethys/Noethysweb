# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)
from django.conf import settings
from django.db.models import Q
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from core.models import Activite, Rattachement, RegimeAlimentaire, Information
from core.utils import utils_dates, utils_impression


class Impression(utils_impression.Impression):
    def __init__(self, *args, **kwds):
        if kwds["dict_donnees"]["orientation"] == "paysage":
            kwds["taille_page"] = landscape(A4)
        else:
            kwds["taille_page"] = portrait(A4)
        utils_impression.Impression.__init__(self, *args, **kwds)

    def Draw(self):
        # Importation des individus rattachés
        param_activites = self.dict_donnees["activites"]
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        conditions = Q(individu__inscription__activite__in=liste_activites)
        if self.dict_donnees["presents"]:
            conditions &= Q(individu__inscription__consommation__date__gte=self.dict_donnees["presents"][0], individu__inscription__consommation__date__lte=self.dict_donnees["presents"][1])
        rattachements_temp = Rattachement.objects.select_related("individu", "famille", "individu__medecin").prefetch_related("individu__regimes_alimentaires").filter(conditions).distinct().order_by("individu__nom", "individu__prenom")

        # Importation de toutes les informations
        dict_informations = {}
        for information in Information.objects.filter(diffusion_listing_enfants=True).order_by("intitule"):
            dict_informations.setdefault(information.individu_id, [])
            dict_informations[information.individu_id].append(information)

        # Conserve uniquement ceux qui ont des informations
        rattachements = []
        for rattachement in rattachements_temp:
            if rattachement.individu.regimes_alimentaires.all() or rattachement.individu_id in dict_informations:
                rattachements.append(rattachement)

        if not rattachements:
            self.erreurs.append("Aucun individu n'a été trouvé avec les paramètres donnés")

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_detail = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=6, textColor="gray", spaceAfter=0, leading=8)

        # Création du titre du document
        self.Insert_header()

        def Img(fichier=""):
            return "<img src='%s/images/%s' width='6' height='6' valign='middle'/> " % (settings.STATIC_ROOT, fichier)

        # Préparation du tableau
        largeur_contenu = self.taille_page[0] - 75
        dataTableau = [("Individu", "Informations et recommandations", "Régimes alimentaires")]
        largeursColonnes = [120, largeur_contenu-260, 140]

        # Remplissage du tableau
        for rattachement in rattachements:
            ligne = []

            # Identité de l'individu
            detail = ""
            if rattachement.individu.date_naiss:
                detail += "né%s le %s" % ("e" if rattachement.individu.civilite in (2, 3, 5) else "", utils_dates.ConvertDateToFR(rattachement.individu.date_naiss))
            if rattachement.individu.info_garde:
                detail += "<br/><font color='red'>Info garde : %s</font>" % rattachement.individu.info_garde
            ligne.append([Paragraph(rattachement.individu.Get_nom(), style_centre), Paragraph(detail, style_detail)])

            # Informations
            contenu_tableau = []
            for information in dict_informations.get(rattachement.individu_id, []):
                texte = "<b>%s</b>" % information.intitule
                if information.description:
                    texte += " : %s" % information.description
                contenu_tableau.append(Paragraph(texte, style_defaut))
            ligne.append(contenu_tableau)

            # Régimes alimentaires
            texte_regimes = ", ".join([regime.nom for regime in rattachement.individu.regimes_alimentaires.all()])
            ligne.append([Paragraph(texte_regimes, style_defaut)])

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, -1), "Helvetica", 7),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
        ])
        # Création du tableau
        tableau = Table(dataTableau, largeursColonnes)
        tableau.setStyle(style)
        self.story.append(tableau)
