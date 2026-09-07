# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, csv
from django.conf import settings
from core.models import Facture, Depot, Reglement, Ventilation
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


# Conventions par défaut selon la gamme Sage visée.
# "analytique" : "colonne" = une simple colonne Section analytique ;
#                "double" = doublement des lignes de classe 7 (Type G/A) propre à Sage 100.

PRESETS_SAGE = {
    "sage50":      {"libelle": "Sage 50 / Sage 50cloud Compta (ex-Ciel)", "compte_clients": "411000",   "separateur": "point_virgule", "format_date": "jjmmaaaa", "analytique": "colonne"},
    "sage100":     {"libelle": "Sage 100 / Sage 100cloud Comptabilité",   "compte_clients": "41100000", "separateur": "tabulation",    "format_date": "jjmmaaaa", "analytique": "colonne"},
    "sage100_ana": {"libelle": "Sage 100 - Analytique par doublement",     "compte_clients": "41100000", "separateur": "tabulation",    "format_date": "jjmmaaaa", "analytique": "double"},
    "ligne30":     {"libelle": "Sage Ligne 30 / i7",                       "compte_clients": "411000",   "separateur": "point_virgule", "format_date": "jjmmaaaa", "analytique": "colonne"},
}


class Exporter(BaseExporter):
    def Generer(self):
        self.version = self.options.get("version_sage", "sage100")
        self.preset = PRESETS_SAGE.get(self.version, PRESETS_SAGE["sage100"])
        self.mode_analytique = self.preset["analytique"]

        self.nom_fichier = "export_sage_%s_%s.csv" % (self.version, datetime.date.today().strftime("%Y-%m-%d"))
        self.Creer_repertoire_sortie(nom_rep="sage")
        if not self.Creation_fichier():
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, "sage", self.nom_fichier)

    def Get_separateur(self):
        """ Renvoie le séparateur de colonnes choisi """
        return {"point_virgule": ";", "tabulation": "\t", "virgule": ",", "barre": "|"}.get(self.options["separateur"], ";")

    def Formate_date(self, date=None):
        """ Formate une date selon le format choisi """
        if not date:
            return ""
        if self.options["format_date"] == "aaaammjj":
            return date.strftime("%Y%m%d")
        return date.strftime("%d/%m/%Y")

    def Formate_montant(self, montant=None):
        """ Formate un montant avec le séparateur décimal choisi """
        texte = "%.2f" % (montant or 0.0)
        # Si le séparateur de colonnes est la virgule, on force le point décimal pour éviter les conflits
        if self.options["separateur"] != "virgule" and self.options["separateur_decimal"] == "virgule":
            texte = texte.replace(".", ",")
        return texte

    def Get_code_tiers(self, famille=None):
        """ Renvoie le code tiers de la famille (code comptable ou code généré) """
        return famille.code_compta or "FAM%06d" % famille.pk

    def Get_colonnes(self):
        """ Renvoie la liste ordonnée des colonnes selon le mode analytique """
        if self.mode_analytique == "double":
            # Format Sage 100 avec analytique par doublement des lignes (Type G = générale, A = analytique)
            return [
                "Type", "Journal", "Date", "Compte général", "Compte tiers",
                "Numéro de pièce", "Référence", "Libellé", "Débit", "Crédit",
                "Date d'échéance", "Plan analytique", "Section analytique",
            ]
        # Format standard : section analytique sur une simple colonne
        return [
            "Journal", "Date", "Compte général", "Compte tiers",
            "Numéro de pièce", "Référence", "Libellé", "Débit", "Crédit",
            "Date d'échéance", "Section analytique",
        ]

    def Nouvelle_ligne(self, type_ecriture="G", **kwargs):
        """ Construit une ligne pré-remplie de vides, en ajoutant la colonne Type si nécessaire """
        ligne = {colonne: "" for colonne in self.colonnes}
        if "Type" in self.colonnes:
            ligne["Type"] = type_ecriture
        for cle, valeur in kwargs.items():
            ligne[cle] = valeur
        return ligne

    def Creation_fichier(self):
        # Récupération de la période
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(self.options["periode"])
        self.colonnes = self.Get_colonnes()

        chemin_fichier = os.path.join(self.rep_destination, self.nom_fichier)
        with open(chemin_fichier, "w", newline="", encoding="utf-8") as fichier_csv:
            writer = csv.DictWriter(fichier_csv, fieldnames=self.colonnes, delimiter=self.Get_separateur())
            if self.options["entete"]:
                writer.writeheader()

            # ----- Intégration des factures (Journal des ventes) -----
            factures = Facture.objects.select_related("famille").filter(date_edition__gte=date_debut, date_edition__lte=date_fin, etat__isnull=True).order_by("pk")
            details_factures = self.Get_detail_factures(factures=factures)
            for facture in factures:
                code_tiers = self.Get_code_tiers(famille=facture.famille)
                num_piece = str(facture.numero)
                date_edition = self.Formate_date(facture.date_edition)
                date_echeance = self.Formate_date(facture.date_echeance)

                # Lignes de produits (Crédit) - un compte général par nature de prestation
                for ligne_detail in details_factures.get(facture, []):
                    section = ligne_detail["code_analytique"] or ""

                    # Ligne générale (Type G)
                    writer.writerow(self.Nouvelle_ligne(
                        type_ecriture="G",
                        **{
                            "Journal": self.options["code_journal_ventes"],
                            "Date": date_edition,
                            "Compte général": ligne_detail["code_compta"] or "",
                            "Numéro de pièce": num_piece,
                            "Référence": num_piece,
                            "Libellé": ligne_detail["label"],
                            "Crédit": self.Formate_montant(ligne_detail["montant"]),
                            "Date d'échéance": date_echeance,
                            # Section analytique sur colonne simple (modes non "double")
                            "Section analytique": section if self.mode_analytique != "double" else "",
                        }
                    ))

                    # Ligne analytique additionnelle (Type A) - propre au format Sage 100 par doublement
                    if self.mode_analytique == "double" and section:
                        writer.writerow(self.Nouvelle_ligne(
                            type_ecriture="A",
                            **{
                                "Journal": self.options["code_journal_ventes"],
                                "Date": date_edition,
                                "Compte général": ligne_detail["code_compta"] or "",
                                "Numéro de pièce": num_piece,
                                "Référence": num_piece,
                                "Libellé": ligne_detail["label"],
                                "Crédit": self.Formate_montant(ligne_detail["montant"]),
                                "Plan analytique": self.options.get("plan_analytique", "") or "",
                                "Section analytique": section,
                            }
                        ))

                # Ligne de contrepartie client (Débit sur le compte 411xxx)
                writer.writerow(self.Nouvelle_ligne(
                    type_ecriture="G",
                    **{
                        "Journal": self.options["code_journal_ventes"],
                        "Date": date_edition,
                        "Compte général": self.options["compte_clients"],
                        "Compte tiers": code_tiers,
                        "Numéro de pièce": num_piece,
                        "Référence": num_piece,
                        "Libellé": "Facture %s" % facture.numero,
                        "Débit": self.Formate_montant(facture.total),
                        "Date d'échéance": date_echeance,
                    }
                ))

            # ----- Intégration des règlements (Journal de banque) -----
            depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")
            ventilations = Ventilation.objects.select_related("reglement", "prestation", "prestation__facture").filter(reglement__depot__in=depots, prestation__facture__isnull=False)
            dict_reglements_factures = {ventilation.reglement: ventilation.prestation.facture.numero for ventilation in ventilations}

            for depot in depots:
                num_piece = "DEP%06d" % depot.pk
                date_depot = self.Formate_date(depot.date)
                dernier_reglement = None

                # Une ligne par règlement (Crédit sur le compte 411xxx du client)
                for reglement in Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot):
                    dernier_reglement = reglement
                    num_facture = dict_reglements_factures.get(reglement, "")
                    writer.writerow(self.Nouvelle_ligne(
                        type_ecriture="G",
                        **{
                            "Journal": reglement.mode.code_journal or self.options["code_journal_reglements"],
                            "Date": date_depot,
                            "Compte général": self.options["compte_clients"],
                            "Compte tiers": self.Get_code_tiers(famille=reglement.famille),
                            "Numéro de pièce": num_piece,
                            "Référence": reglement.numero_piece or "",
                            "Libellé": "Règlement %s%s" % (reglement.famille.nom, " - Facture %s" % num_facture if num_facture else ""),
                            "Crédit": self.Formate_montant(reglement.montant),
                        }
                    ))

                # Ligne de contrepartie banque (Débit sur le compte de trésorerie du dépôt)
                code_journal = dernier_reglement.mode.code_journal if (dernier_reglement and dernier_reglement.mode.code_journal) else self.options["code_journal_reglements"]
                writer.writerow(self.Nouvelle_ligne(
                    type_ecriture="G",
                    **{
                        "Journal": code_journal,
                        "Date": date_depot,
                        "Compte général": depot.code_compta or "",
                        "Numéro de pièce": num_piece,
                        "Libellé": depot.nom,
                        "Débit": self.Formate_montant(depot.montant or 0.0),
                    }
                ))

        return True
