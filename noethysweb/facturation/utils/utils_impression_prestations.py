# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Prestation, Activite
from core.utils import utils_impression, utils_texte


class Impression(utils_impression.Impression):
    def Draw(self):
        # Importation des prestations
        conditions = Q(date__range=self.dict_donnees["periode"])

        if self.dict_donnees["activites"]["type"] == "groupes_activites":
            liste_activites = [activite.pk for activite in Activite.objects.filter(groupes_activites__in=self.dict_donnees["activites"]["ids"])]
        else:
            liste_activites = self.dict_donnees["activites"]["ids"]
        conditions &= Q(activite_id__in=liste_activites)

        prestations = Prestation.objects.select_related("famille", "activite", "individu", "facture").filter(conditions).order_by("individu__prenom")

        # Regroupement des prestations par famille et application filtre ville
        dict_prestations = {}
        for prestation in prestations:
            if not self.dict_donnees["filtre_villes"] or (self.dict_donnees["filtre_villes"] == "SELECTION" and prestation.famille.ville_resid and prestation.famille.ville_resid.upper() in self.dict_donnees["villes"]):
                dict_prestations.setdefault(prestation.famille, [])
                dict_prestations[prestation.famille].append(prestation)

        # Préparation du détail
        dict_prestations_famille = {}
        for famille in dict_prestations.keys():
            dict_prestations_famille.setdefault(famille, [])

            dict_prestations_temp = {}
            for prestation in dict_prestations.get(famille, []):
                prix_unitaire = prestation.montant / prestation.quantite
                if prestation.individu:
                    libelle = "%s - %s" % (prestation.individu.prenom or prestation.individu.nom, prestation.label)
                else:
                    libelle = prestation.label
                key = (libelle, prix_unitaire)
                dict_prestations_temp.setdefault(key, {"quantite": 0, "montant": decimal.Decimal(0), "label": prestation.label, "individus": {}})
                dict_prestations_temp[key]["quantite"] += prestation.quantite
                dict_prestations_temp[key]["montant"] += prestation.montant
                if prestation.individu:
                    dict_prestations_temp[key]["individus"][prestation.individu] = True

            keys = list(dict_prestations_temp.keys())
            keys.sort()
            for key in keys:
                dict_prestation = dict_prestations_temp[key]
                dict_prestation.update({"libelle": key[0], "prix": key[1]})
                dict_prestations_famille[famille].append(dict_prestation)

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)

        # Création du titre du document
        self.Insert_header()

        # Sous-titre
        self.story.append(Paragraph("<b>Période du %s au %s</b>" % (self.dict_donnees["periode"][0].strftime("%d/%m/%Y"), self.dict_donnees["periode"][1].strftime("%d/%m/%Y")), style_centre))
        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [("Famille", "Montant", "Détail", "Qté", "Prix", "Total")]

        keys = sorted(list(dict_prestations_famille.keys()), key=lambda x: x.nom)
        for famille in keys:

            ligne = []

            # Famille
            texte = "%s<br/>%s<br/>%s %s" % (famille, famille.Get_rue_resid() or "", famille.cp_resid or "", famille.ville_resid or "")
            ligne.append(Paragraph(texte, style_defaut))

            # Montant de la facture
            ligne.append(Paragraph(utils_texte.Formate_montant(sum([ligne_detail["montant"] for ligne_detail in dict_prestations_famille[famille]])), style_centre))

            # Libellé prestation
            ligne.append(Paragraph("<br/>".join([ligne_detail["libelle"] for ligne_detail in dict_prestations_famille[famille]]), style_defaut))

            # Quantité
            ligne.append(Paragraph("<br/>".join([str(ligne_detail["quantite"]) for ligne_detail in dict_prestations_famille[famille]]), style_centre))

            # Prix unitaire
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["prix"]) for ligne_detail in dict_prestations_famille[famille]]), style_centre))

            # Montant ligne de détail
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["montant"]) for ligne_detail in dict_prestations_famille[famille]]), style_centre))

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
        tableau = Table(dataTableau, [170, 50, 160, 40, 50, 50], repeatRows=1)
        tableau.setStyle(style)
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Récapitulatif
        lignes_recap = {}
        totaux = {"quantite": 0, "montant": decimal.Decimal(0)}
        for famille, lignes_detail in dict_prestations_famille.items():
            for ligne_detail in lignes_detail:
                key = (ligne_detail["label"], ligne_detail["prix"])
                lignes_recap.setdefault(key, {"quantite": 0, "montant": decimal.Decimal(0), "familles": {}, "individus": {}})
                lignes_recap[key]["quantite"] += ligne_detail["quantite"]
                lignes_recap[key]["montant"] += ligne_detail["montant"]
                lignes_recap[key]["familles"][famille] = True
                lignes_recap[key]["individus"].update(ligne_detail["individus"])
                totaux["quantite"] += ligne_detail["quantite"]
                totaux["montant"] += ligne_detail["montant"]

        keys = list(lignes_recap.keys())
        keys.sort()

        dataTableau = [("Prestation", "Nbre familles", "Nbre individus", "Tarif unitaire", "Quantité", "Total")]
        for key in keys:
            ligne_recap = lignes_recap[key]
            dataTableau.append((
                Paragraph(key[0], style_centre),
                Paragraph(str(len(ligne_recap["familles"])), style_centre),
                Paragraph(str(len(ligne_recap["individus"])), style_centre),
                Paragraph(utils_texte.Formate_montant(key[1]), style_centre),
                Paragraph(str(ligne_recap["quantite"]), style_centre),
                Paragraph(utils_texte.Formate_montant(ligne_recap["montant"]), style_centre),
            ))
        dataTableau.append((
            Paragraph("", style_centre), Paragraph("", style_centre), Paragraph("", style_centre), Paragraph("", style_centre),
            Paragraph("<b>%s</b>" % totaux["quantite"], style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(totaux["montant"]), style_centre),
        ))
        tableau = Table(dataTableau, [195, 65, 65, 65, 65, 65])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.black),
            ("GRID", (-2, -1), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ]))
        self.story.append(tableau)
