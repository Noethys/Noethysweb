# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
from django.db.models import Q, Sum, Count
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from core.models import Facture, Prestation, Prelevements, PesPiece
from core.utils import utils_impression, utils_texte


class Impression(utils_impression.Impression):
    def Draw(self):
        # Importation des factures
        if self.dict_donnees["type_selection"] == "LOT":
            filtres_factures = Q(lot=self.dict_donnees["lot"])
            titre = self.dict_donnees["lot"].nom
        if self.dict_donnees["type_selection"] == "DATE_EDITION":
            filtres_factures = Q(date_edition__range=self.dict_donnees["date_edition"])
            titre = "Factures éditées entre le %s et le %s" % (self.dict_donnees["date_edition"][0].strftime("%d/%m/%Y"), self.dict_donnees["date_edition"][1].strftime("%d/%m/%Y"))
        factures = Facture.objects.select_related("famille").filter(filtres_factures).order_by("famille__nom")

        # Prélèvements
        dict_prelevements = {prelevement.facture_id: prelevement for prelevement in Prelevements.objects.filter(facture__in=factures)}
        dict_pes = {piece.facture_id: piece for piece in PesPiece.objects.filter(facture__in=factures)}

        # Importation des prestations
        dict_prestations = {}
        for prestation in Prestation.objects.select_related("activite", "individu", "facture").filter(facture__in=factures).order_by("individu__prenom"):
            dict_prestations.setdefault(prestation.facture, [])
            dict_prestations[prestation.facture].append(prestation)

        # Préparation du détail des factures
        dict_prestations_facture = {}
        for facture in factures:
            dict_prestations_facture.setdefault(facture, [])

            dict_prestations_temp = {}
            for prestation in dict_prestations.get(facture, []):
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
                dict_prestations_facture[facture].append(dict_prestation)

        # Importation des stats
        stats = factures.aggregate(total=Sum("total"), nbre=Count("idfacture"))

        # Préparation des polices
        style_defaut = ParagraphStyle(name="defaut", fontName="Helvetica", fontSize=7, spaceAfter=0, leading=9)
        style_centre = ParagraphStyle(name="centre", fontName="Helvetica", alignment=1, fontSize=7, spaceAfter=0, leading=9)
        style_titre = ParagraphStyle(name="titre", fontName="Helvetica-bold", alignment=1, fontSize=11, spaceAfter=0, leading=11)

        # Création du titre du document
        self.Insert_header()

        # Tableau de description du lot
        dataTableau = [(
            Paragraph(titre, style_titre),
        )]
        tableau = Table(dataTableau, [520,])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        self.story.append(tableau)

        # Tableau des totaux du lot
        dataTableau = [(
            Paragraph("Total : <b>%s (%d)</b>" % (utils_texte.Formate_montant(stats["total"]), stats["nbre"]), style_centre),
        )]
        tableau = Table(dataTableau, [520,])
        tableau.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
        ]))
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Remplissage du tableau
        dataTableau = [("N° Facture", "Famille", "Montant", "Détail", "Qté", "Prix", "Total")]

        for facture in factures:
            ligne = []

            # N° Facture
            ligne.append(facture.numero)

            # Famille
            texte = "%s<br/>%s<br/>%s %s" % (facture.famille, facture.famille.Get_rue_resid() or "", facture.famille.cp_resid or "", facture.famille.ville_resid or "")
            ligne.append(Paragraph(texte, style_defaut))

            # Montant de la facture
            texte_montant = utils_texte.Formate_montant(facture.total)
            if facture.pk in dict_prelevements or facture.pk in dict_pes:
                texte_montant += "<br/>(Prélevé)"
            ligne.append(Paragraph(texte_montant, style_centre))

            # Libellé prestation
            ligne.append(Paragraph("<br/>".join([ligne_detail["libelle"] for ligne_detail in dict_prestations_facture[facture]]), style_defaut))

            # Quantité
            ligne.append(Paragraph("<br/>".join([str(ligne_detail["quantite"]) for ligne_detail in dict_prestations_facture[facture]]), style_centre))

            # Prix unitaire
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["prix"]) for ligne_detail in dict_prestations_facture[facture]]), style_centre))

            # Montant ligne de détail
            ligne.append(Paragraph("<br/>".join([utils_texte.Formate_montant(ligne_detail["montant"]) for ligne_detail in dict_prestations_facture[facture]]), style_centre))

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
        tableau = Table(dataTableau, [45, 170, 45, 145, 30, 40, 45], repeatRows=1)
        tableau.setStyle(style)
        self.story.append(tableau)

        self.story.append(Spacer(0, 15))

        # Récapitulatif
        lignes_recap = {}
        totaux = {"quantite": 0, "montant": decimal.Decimal(0)}
        for facture, lignes_detail in dict_prestations_facture.items():
            for ligne_detail in lignes_detail:
                key = (ligne_detail["label"], ligne_detail["prix"])
                lignes_recap.setdefault(key, {"quantite": 0, "montant": decimal.Decimal(0), "familles": {}, "individus": {}})
                lignes_recap[key]["quantite"] += ligne_detail["quantite"]
                lignes_recap[key]["montant"] += ligne_detail["montant"]
                lignes_recap[key]["familles"][facture.famille] = True
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
