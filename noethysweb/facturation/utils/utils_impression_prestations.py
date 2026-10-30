# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q, Count
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Prestation, Activite, Famille
from core.utils import utils_impression, utils_texte, utils_polices


class Impression(utils_impression.Impression):
    def Draw(self):
        detail_prix_unitaire = self.dict_donnees["detail_prix_unitaire"]

        # Importation des prestations
        conditions = Q(date__range=self.dict_donnees["periode"], famille__isnull=False)

        if self.dict_donnees["activites"]["type"] == "groupes_activites":
            liste_activites = list(Activite.objects.filter(groupes_activites__in=self.dict_donnees["activites"]["ids"]).values_list("pk", flat=True))
        else:
            liste_activites = self.dict_donnees["activites"]["ids"]
        conditions &= Q(activite_id__in=liste_activites)

        # Optimisation : pré-regroupement des prestations identiques directement dans la base de données.
        # Seuls les champs utiles sont lus (aucun champ chiffré n'est chargé, donc aucun déchiffrement ici).
        prestations = Prestation.objects.filter(conditions).order_by().values(
            "famille_id", "individu_id", "individu__prenom", "individu__nom", "label", "montant", "quantite"
        ).annotate(nbre=Count("pk"))

        # Chargement des familles concernées : une seule fois par famille et uniquement les champs nécessaires
        familles = Famille.objects.filter(pk__in=Prestation.objects.filter(conditions).values("famille_id")).only("nom", "rue_resid", "cp_resid", "ville_resid")

        # Application du filtre sur les villes
        filtre_villes = self.dict_donnees["filtre_villes"]
        villes = set(self.dict_donnees["villes"] or [])
        dict_familles = {}
        for famille in familles:
            if not filtre_villes or (filtre_villes == "SELECTION" and famille.ville_resid and famille.ville_resid.upper() in villes):
                dict_familles[famille.pk] = famille

        # Préparation du détail
        dict_temp = {}
        for prestation in prestations:
            famille = dict_familles.get(prestation["famille_id"])
            if not famille:
                continue
            quantite = prestation["quantite"] or 0
            montant = prestation["montant"] or decimal.Decimal(0)
            prix_unitaire = (montant / quantite) if detail_prix_unitaire else 0
            if prestation["individu_id"]:
                libelle = "%s - %s" % (prestation["individu__prenom"] or prestation["individu__nom"], prestation["label"])
            else:
                libelle = prestation["label"]
            dict_prestations_temp = dict_temp.setdefault(famille, {})
            dict_prestation = dict_prestations_temp.setdefault((libelle, prix_unitaire), {"quantite": 0, "montant": decimal.Decimal(0), "label": prestation["label"], "individus": {}})
            dict_prestation["quantite"] += quantite * prestation["nbre"]
            dict_prestation["montant"] += montant * prestation["nbre"]
            if prestation["individu_id"]:
                dict_prestation["individus"][prestation["individu_id"]] = True

        dict_prestations_famille = {}
        for famille, dict_prestations_temp in dict_temp.items():
            dict_prestations_famille[famille] = []
            for key in sorted(dict_prestations_temp.keys()):
                dict_prestation = dict_prestations_temp[key]
                dict_prestation.update({"libelle": key[0], "prix": key[1]})
                dict_prestations_famille[famille].append(dict_prestation)

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName=utils_polices.FONT_NORMAL, fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName=utils_polices.FONT_NORMAL, alignment=1, fontSize=7, spaceAfter=0, leading=9)

        # Création du titre du document
        self.Insert_header()

        # Sous-titre
        self.story.append(Paragraph("<b>Période du %s au %s</b>" % (self.dict_donnees["periode"][0].strftime("%d/%m/%Y"), self.dict_donnees["periode"][1].strftime("%d/%m/%Y")), style_centre))
        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [["Famille", "Montant", "Détail", "Qté", "Total"]]
        if self.dict_donnees["detail_prix_unitaire"]:
            dataTableau[0].insert(4, "Prix")

        keys = sorted(dict_prestations_famille.keys(), key=lambda x: (x.nom or "", x.pk))
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
            if self.dict_donnees["detail_prix_unitaire"]:
                ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["prix"]) for ligne_detail in dict_prestations_famille[famille]]), style_centre))

            # Montant ligne de détail
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["montant"]) for ligne_detail in dict_prestations_famille[famille]]), style_centre))

            # Finalisation de la ligne
            dataTableau.append(ligne)

        # Finalisation du tableau
        style = TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ])
        # Création du tableau
        largeurs_colonnes = [170, 50, 160, 40, 50, 50] if self.dict_donnees["detail_prix_unitaire"] else [220, 50, 160, 40, 50]
        tableau = Table(dataTableau, largeurs_colonnes, repeatRows=1)
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

        dataTableau = [["Prestation", "Nbre familles", "Nbre individus", "Quantité", "Total"]]
        if self.dict_donnees["detail_prix_unitaire"]:
            dataTableau[0].insert(3, "Tarif unitaire")

        for key in keys:
            ligne_recap = lignes_recap[key]
            ligne = [
                Paragraph(key[0], style_centre),
                Paragraph(str(len(ligne_recap["familles"])), style_centre),
                Paragraph(str(len(ligne_recap["individus"])), style_centre),
                Paragraph(str(ligne_recap["quantite"]), style_centre),
                Paragraph(utils_texte.Formate_montant(ligne_recap["montant"]), style_centre),
            ]
            if self.dict_donnees["detail_prix_unitaire"]:
                ligne.insert(3, Paragraph(utils_texte.Formate_montant(key[1]), style_centre))
            dataTableau.append(ligne)

        ligne = [
            Paragraph("", style_centre), Paragraph("", style_centre), Paragraph("", style_centre),
            Paragraph("<b>%s</b>" % totaux["quantite"], style_centre), Paragraph("<b>%s</b>" % utils_texte.Formate_montant(totaux["montant"]), style_centre),
        ]
        if self.dict_donnees["detail_prix_unitaire"]:
            ligne.insert(3, Paragraph("", style_centre))
        dataTableau.append(ligne)

        largeurs_colonnes = [195, 65, 65, 65, 65, 65] if self.dict_donnees["detail_prix_unitaire"] else [260, 65, 65, 65, 65]
        tableau = Table(dataTableau, largeurs_colonnes)
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.black),
            ("GRID", (-2, -1), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTRE"),
        ]))
        self.story.append(tableau)
