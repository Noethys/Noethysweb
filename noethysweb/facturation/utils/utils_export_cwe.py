# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, decimal
from django.conf import settings
from core.models import Facture, Depot, Reglement, Ventilation
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


class Exporter(BaseExporter):
    def Generer(self):
        # Création du répertoire de sortie et des fichiers
        self.Creer_repertoire_sortie(nom_rep="cwe")

        import xlsxwriter
        nom_fichier = "export_cwe.xlsx"
        classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier))
        if not self.Creation_fichier(classeur=classeur):
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier)

    def Creation_fichier(self, classeur=None):
        # Récupération de la période
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(self.options["periode"])

        lignes = []

        # Recherche des factures
        factures = Facture.objects.select_related("famille").filter(date_edition__gte=date_debut, date_edition__lte=date_fin).order_by("pk")
        details_factures = self.Get_detail_factures(factures=factures)
        for facture in factures:
            for ligne_detail in details_factures.get(facture, []):
                ligne = {
                    "libelle": "%s - Client %s" % (ligne_detail["label"], facture.famille.code_compta or facture.famille.pk),
                    "date": facture.date_edition.strftime("%d-%m-%Y"),
                    "piece": "FAC %s" % facture.numero,
                    "code": "VE",
                    "client": facture.famille.code_compta or facture.famille.pk,
                }
                lignes.append({**ligne, **{"debit": decimal.Decimal(0), "credit": ligne_detail["montant"], "compte": ligne_detail["code_compta"]}})
                lignes.append({**ligne, **{"credit": decimal.Decimal(0), "debit": ligne_detail["montant"], "compte": self.options["compte_clients"]}})

        # Recherche des règlements
        depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")
        ventilations = Ventilation.objects.select_related("reglement", "prestation", "prestation__facture").filter(reglement__depot__in=depots, prestation__facture__isnull=False)
        dict_reglements_factures = {ventilation.reglement: ventilation.prestation.facture.numero for ventilation in ventilations}

        for depot in depots:
            for reglement in Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot):
                ligne = {
                    "libelle": "Règlement facture - %s - Client %s" % (reglement.mode.label, reglement.famille.code_compta or reglement.famille.pk),
                    "date": depot.date.strftime("%d-%m-%Y"),
                    "piece": "FAC %s" % dict_reglements_factures.get(reglement, ""),
                    "code": reglement.mode.code_journal,
                    "client": reglement.famille.code_compta or reglement.famille.pk,
                }
                lignes.append({**ligne, **{"debit": reglement.montant, "credit": decimal.Decimal(0), "compte": depot.code_compta or reglement.mode.code_compta}})
                lignes.append({**ligne, **{"credit": reglement.montant, "debit": decimal.Decimal(0), "compte": self.options["compte_clients"]}})

        # Création du fichier xlsx
        feuille = classeur.add_worksheet("Page 1")
        format_money = classeur.add_format({"num_format": "# ##0.00"})

        # Insertion des entêtes de colonnes
        for index_colonne, (titre_colonne, largeur_colonne) in enumerate([("N° Ecriture", 10), ("Libellé", 55), ("Débit", 11), ("Crédit", 11), ("Compte", 12), ("Date", 12), ("Pièce", 20), ("Code", 10), ("N° Client", 25)]):
            feuille.write(0, index_colonne, titre_colonne)
            feuille.set_column(index_colonne, index_colonne, largeur_colonne)

        # Insertion des lignes
        for index_ligne, ligne in enumerate(lignes, 1):
            feuille.write(index_ligne, 0, index_ligne)
            for index_colonne, (code_colonne, format_case) in enumerate([("libelle", None), ("debit", format_money), ("credit", format_money), ("compte", None), ("date", None), ("piece", None), ("code", None), ("client", None)], 1):
                feuille.write(index_ligne, index_colonne, ligne.get(code_colonne, ""), format_case)

        classeur.close()
        return True
