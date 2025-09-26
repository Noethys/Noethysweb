# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, csv
from django.conf import settings
from core.models import Famille, Facture, Depot, Reglement, Ventilation
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


class Exporter(BaseExporter):
    def Generer(self):
        self.nom_fichier = "export_ebp_%s.csv" % datetime.date.today().strftime("%Y-%m-%d")
        self.Creer_repertoire_sortie(nom_rep="ebp")
        if not self.Creation_fichier():
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, "ebp", self.nom_fichier)

    def Creation_fichier(self):
        # Récupération de la période
        date_debut = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[1])

        # Préparation du csv
        champs_ebp = [
            "Date", "Journal", "N° compte général", "N° compte tiers",
            "N° facture", "Libellé", "Débit", "Crédit", "Code Analytique",
            "Date de pièce", "Référence", "Mode de règlement", "Date d'échéance"
        ]
        with open(os.path.join(self.rep_destination, self.nom_fichier), "w", newline="", encoding="utf-8") as fichier_csv:
            writer = csv.DictWriter(fichier_csv, fieldnames=champs_ebp, delimiter=";")
            writer.writeheader()

            # Intégration des factures
            factures = Facture.objects.select_related("famille").filter(date_edition__gte=date_debut, date_edition__lte=date_fin).order_by("pk")
            details_factures = self.Get_detail_factures(factures=factures)
            for index_facture, facture in enumerate(factures, 1):

                # Ligne compte général
                for index_ligne_detail, ligne_detail in enumerate(details_factures.get(facture, []), 1):
                    ligne = {}
                    ligne["Date"] = facture.date_edition.strftime("%d/%m/%Y")
                    ligne["Journal"] = "VE"
                    ligne["N° compte général"] = ligne_detail["code_compta"]
                    ligne["Code Analytique"] = ligne_detail["code_analytique"]
                    ligne["N° facture"] = facture.numero
                    ligne["Libellé"] = ligne_detail["label"]
                    ligne["Crédit"] = "%.2f" % ligne_detail["montant"]
                    ligne["Référence"] = facture.numero
                    ligne["Date de pièce"] = facture.date_edition.strftime("%d/%m/%Y")
                    ligne["Date d'échéance"] = facture.date_echeance.strftime("%d/%m/%Y") if facture.date_echeance else ""
                    writer.writerow(ligne)

                # Ligne compte client (411xxx)
                ligne = {}
                ligne["Date"] = facture.date_edition.strftime("%d/%m/%Y")
                ligne["Journal"] = "VE"
                ligne["N° compte général"] = facture.famille.code_compta or "FAM%06d" % facture.famille.pk
                ligne["N° compte tiers"] = facture.famille.code_compta or "FAM%06d" % facture.famille.pk
                ligne["N° facture"] = facture.numero
                ligne["Libellé"] = "Facture %s" % facture.numero
                ligne["Débit"] = "%.2f" % facture.solde
                ligne["Référence"] = facture.numero
                ligne["Date de pièce"] = facture.date_edition.strftime("%d/%m/%Y")
                ligne["Date d'échéance"] = facture.date_echeance.strftime("%d/%m/%Y") if facture.date_echeance else ""
                writer.writerow(ligne)

            # Intégration des règlements
            depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")
            ventilations = Ventilation.objects.select_related("reglement", "prestation", "prestation__facture").filter(reglement__depot__in=depots, prestation__facture__isnull=False)
            dict_reglements_factures = {ventilation.reglement: ventilation.prestation.facture.numero for ventilation in ventilations}
            for index_depot, depot in enumerate(depots, 1):

                # Ligne du règlement
                dernier_reglement = None
                for index_reglement, reglement in enumerate(Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot), 1):
                    dernier_reglement = reglement
                    ligne = {}
                    ligne["Date"] = depot.date.strftime("%d/%m/%Y")
                    ligne["N° compte général"] = reglement.famille.code_compta or "FAM%06d" % reglement.famille.pk
                    ligne["N° compte tiers"] = reglement.famille.code_compta or "FAM%06d" % reglement.famille.pk
                    ligne["Journal"] = reglement.mode.code_journal or "BQ"
                    ligne["Libellé"] = "Règlement %s" % reglement.famille.nom
                    ligne["Référence"] = reglement.numero_piece or ""
                    ligne["Crédit"] = "%.2f" % reglement.montant
                    ligne["N° facture"] = dict_reglements_factures.get(reglement, "")
                    ligne["Date de pièce"] = depot.date.strftime("%d/%m/%Y")
                    ligne["Mode de règlement"] = reglement.mode.label
                    writer.writerow(ligne)

                # Ligne du dépôt
                ligne = {}
                ligne["Date"] = depot.date.strftime("%d/%m/%Y")
                ligne["N° compte général"] = depot.code_compta
                ligne["Journal"] = dernier_reglement.mode.code_journal if dernier_reglement and dernier_reglement.mode.code_journal else "BQ"
                ligne["Débit"] = "%.2f" % (depot.montant or 0.0)
                ligne["Libellé"] = depot.nom
                ligne["Date de pièce"] = depot.date.strftime("%d/%m/%Y")
                writer.writerow(ligne)

        return True
