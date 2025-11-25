# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, shutil
from django.conf import settings
from core.models import Facture, Depot, Reglement, Ventilation
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


class Exporter(BaseExporter):
    def Generer(self):
        # Création du répertoire de sortie et des fichiers
        self.Creer_repertoire_sortie(nom_rep="quadra")
        if not self.Creation_fichiers():
            return False

        # Création du fichier ZIP
        nom_fichier_zip = "export_quadra_%s.zip" % datetime.date.today().strftime("%Y-%m-%d")
        shutil.make_archive(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier_zip.replace(".zip", "")), "zip", self.rep_destination)
        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier_zip)

    def Creation_fichiers(self):
        # Récupération de la période
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(self.options["periode"])

        # Colonnes des 2 fichiers excel
        colonnes = [
            {"code": "code", "titre": "Code journal", "largeur": 12},
            {"code": "date", "titre": "Date", "largeur": 15, "format": "date"},
            {"code": "compte", "titre": "Compte", "largeur": 15},
            {"code": "intitule", "titre": "Intitulé", "largeur": 40},
            {"code": "libelle", "titre": "Libellé", "largeur": 40},
            {"code": "debit", "titre": "Débit", "largeur": 12, "format": "money"},
            {"code": "credit", "titre": "Crédit", "largeur": 12, "format": "money"},
            {"code": "num_piece", "titre": "Num. Pièce", "largeur": 12},
        ]

        # Génération du fichier des factures
        lignes = []
        factures = Facture.objects.select_related("famille").filter(date_edition__gte=date_debut, date_edition__lte=date_fin, etat__isnull=True).order_by("pk")
        details_factures = self.Get_detail_factures(factures=factures)
        for index_facture, facture in enumerate(factures, 1):
            # Ligne famille
            lignes.append({
                "code": self.options["code_journal_ventes"],
                "date": facture.date_edition.strftime("%d/%m/%Y"),
                "compte": facture.famille.code_compta or "FAM%06d" % facture.famille.pk,
                "intitule": facture.famille.nom,
                "libelle": "Facture %s" % facture.numero,
                "debit": "%.2f" % facture.total,
                "num_piece": index_facture,
            })
            # Ligne compte
            for ligne_detail in details_factures.get(facture, []):
                lignes.append({
                    "code": self.options["code_journal_ventes"],
                    "date": facture.date_edition.strftime("%d/%m/%Y"),
                    "compte": ligne_detail["code_compta"],
                    "intitule": ligne_detail["label"],
                    "libelle": "Facture %s" % facture.numero,
                    "credit": "%.2f" % ligne_detail["montant"],
                    "num_piece": index_facture,
                })

            if self.options["ligne_vide"]:
                lignes.append({})

        self.Creation_fichier_xlsx(nom_fichier="ventes.xlsx", lignes=lignes, colonnes=colonnes)

        # Génération du fichier des règlements
        lignes = []
        depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")
        ventilations = Ventilation.objects.select_related("reglement", "prestation", "prestation__facture").filter(reglement__depot__in=depots, prestation__facture__isnull=False)
        dict_reglements_factures = {ventilation.reglement: ventilation.prestation.facture.numero for ventilation in ventilations}
        for index_depot, depot in enumerate(depots, 1):

            # Ligne règlement
            dernier_reglement = None
            for index_reglement, reglement in enumerate(Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot), 1):
                dernier_reglement = reglement
                lignes.append({
                    "code": dernier_reglement.mode.code_journal if dernier_reglement and dernier_reglement.mode.code_journal else self.options["code_journal_reglements"],
                    "date": depot.date.strftime("%d/%m/%Y"),
                    "compte": reglement.famille.code_compta or "FAM%06d" % reglement.famille.pk,
                    "intitule": reglement.famille.nom,
                    "libelle": "Règlement facture %s" % dict_reglements_factures.get(reglement, ""),
                    "credit": "%.2f" % reglement.montant,
                    "num_piece": index_depot,
                })

            # Ligne dépôt
            lignes.append({
                "code": dernier_reglement.mode.code_journal if dernier_reglement and dernier_reglement.mode.code_journal else self.options["code_journal_reglements"],
                "date": depot.date.strftime("%d/%m/%Y"),
                "compte": depot.code_compta,
                "intitule": depot.nom,
                "libelle": depot.nom,
                "debit": "%.2f" % (depot.montant or 0.0),
                "num_piece": index_depot,
            })

            if self.options["ligne_vide"]:
                lignes.append({})

        self.Creation_fichier_xlsx(nom_fichier="reglements.xlsx", lignes=lignes, colonnes=colonnes)

        return True

    def Creation_fichier_xlsx(self, nom_fichier="", lignes=[], colonnes=[]):
        # Création du fichier xlsx
        import xlsxwriter
        classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, self.rep_base, self.rep_destination, nom_fichier))
        feuille = classeur.add_worksheet("Page 1")
        dict_format = {
            "money": classeur.add_format({"num_format": "# ##0.00"}),
            "date": classeur.add_format({"num_format": "dd/mm/yyyy"})
        }

        # Insertion des entêtes de colonnes
        for index_colonne, colonne in enumerate(colonnes):
            feuille.write(0, index_colonne, colonne["titre"])
            feuille.set_column(index_colonne, index_colonne, colonne["largeur"])

        # Insertion des lignes
        for index_ligne, ligne in enumerate(lignes, 1):
            for index_colonne, colonne in enumerate(colonnes, 0):
                feuille.write(index_ligne, index_colonne, ligne.get(colonne["code"], ""), dict_format.get(colonne.get("format")))

        classeur.close()
        return classeur
