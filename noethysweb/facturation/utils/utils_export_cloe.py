# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, shutil, uuid
from django.conf import settings
from django.db.models import Q
from core.models import Famille, Facture, Depot, Reglement, Ventilation
from core.utils import utils_dates
from facturation.utils.utils_export_ecritures import BaseExporter


format_export_cpt = [("num_compte", "Numéro de compte", 10), ("nom", "Raison sociale ou nom", 30),
                     ("adresse", "Adresse", 30), ("complement_adresse", "Complément d'adresse", 30),
                     ("cp", "Code postal", 5), ("ville", "Ville", 44),
                     ("compte_collectif", "Compte collectif pour les comptes clients", 10)]

format_export_fac = [("num_ecriture", "Numéro d'écriture", 6), ("num_ligne_ecriture", "Numéro de ligne d'écriture", 6),
                     ("date_ecriture", "Date d'écriture", 8), ("compte_general", "Compte général", 11),
                     ("compte_analytique", "Compte analytique", 10), ("code_journal", "Code journal", 3),
                     ("type_piece", "Type de pièce", 3), ("num_piece", "Numéro de pièce", 15), ("montant", "Montant", 15),
                     ("libelle", "Libellé de l'écriture", 50), ("date_echeance", "Date d'échéance", 8),
                     ("num_reglement", "Numéro de règlement", 12), ("num_facture", "Numéro de facture", 20)]

format_export_rgl = [("num_ecriture", "Numéro d'écriture", 6), ("num_ligne_ecriture", "Numéro de ligne d'écriture", 6),
                     ("date_ecriture", "Date d'écriture", 8), ("compte_general", "Compte général", 11),
                     ("code_analytique", "Compte analytique", 10), ("code_journal", "Code journal", 3),
                     ("type_piece", "Type de pièce", 3), ("num_piece", "Numéro de pièce", 15), ("montant", "Montant", 15),
                     ("libelle_ecriture", "Libellé de l'écriture", 50), ("date_echeance", "Date d'échéance", 8),
                     ("num_reglement", "Numéro de règlement", 12), ("num_facture", "Numéro de facture", 20),
                     ("emetteur", "Emetteur", 40), ("etablissement_bancaire", "Etablissement bancaire", 40)]


class Exporter(BaseExporter):
    def Generer(self):
        # Création du répertoire de sortie et des fichiers
        self.Creer_repertoire_sortie(nom_rep="cloe")
        if not self.Creation_fichiers():
            return False

        # Création du fichier ZIP
        nom_fichier_zip = "export_cloe_%s.zip" % datetime.date.today().strftime("%Y-%m-%d")
        shutil.make_archive(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier_zip.replace(".zip", "")), "zip", self.rep_destination)
        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier_zip)

    def Get_code_compta_famille(self, famille=None, idfamille=None, code_compta=None):
        if famille:
            idfamille, code_compta = famille.pk, famille.code_compta
        code = code_compta or "FAM%06d" % idfamille
        if self.options["prefixe_c"]:
            code = "C%s" % code
        return code

    def Ecrire_fichier(self, nom_fichier="", format_export=None, lignes=[]):
        texte = self.Generer_fichier_texte(format_export=format_export, lignes=lignes)
        with open(os.path.join(self.rep_destination, "%s-%s.TXT" % (nom_fichier, datetime.date.today().strftime("%d%m%Y"))), "w") as fichier:
            fichier.write(texte)

    def Creation_fichier_comptes(self, date_debut=None, date_fin=None, dict_familles={}):
        """ Génération du fichier des comptes clients selon l'option 'comptes_clients' """
        selection = self.options.get("comptes_clients", "toutes")
        if selection == "aucune":
            return

        familles = Famille.objects.all()
        if selection == "utilisees":
            # Uniquement les familles concernées par les factures et règlements exportés
            factures = Facture.objects.filter(date_edition__gte=date_debut, date_edition__lte=date_fin, etat__isnull=True).values("famille_id")
            reglements = Reglement.objects.filter(depot__date__gte=date_debut, depot__date__lte=date_fin).values("famille_id")
            familles = familles.filter(Q(pk__in=factures) | Q(pk__in=reglements))
        elif selection == "creees_depuis":
            # Uniquement les familles créées depuis la date donnée (incluse)
            familles = familles.filter(date_creation__date__gte=self.options["date_creation_familles"])

        # Seuls les champs utiles sont lus : cela évite de déchiffrer tous les champs chiffrés de chaque famille
        lignes = []
        compte_collectif = self.options["compte_collectif"] or ""
        for idfamille, rue_resid, cp_resid, ville_resid in familles.order_by("nom").values_list("pk", "rue_resid", "cp_resid", "ville_resid"):
            code_famille, nom = dict_familles[idfamille]
            lignes_rue = rue_resid.split("\n") if rue_resid else []
            lignes.append({
                "num_compte": code_famille,
                "nom": nom,
                "adresse": lignes_rue[0] if lignes_rue else "",
                "complement_adresse": lignes_rue[1] if len(lignes_rue) > 1 else "",
                "cp": cp_resid,
                "ville": ville_resid,
                "compte_collectif": compte_collectif,
            })
        self.Ecrire_fichier(nom_fichier="CPT", format_export=format_export_cpt, lignes=lignes)

    def Creation_fichiers(self):
        # Récupération de la période
        date_debut = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[1])

        # Codes et noms de toutes les familles (champs non chiffrés, donc lecture rapide)
        dict_familles = {idfamille: (self.Get_code_compta_famille(idfamille=idfamille, code_compta=code_compta), nom) for idfamille, nom, code_compta in Famille.objects.values_list("pk", "nom", "code_compta")}

        # Génération du fichier des comptes auxiliaires
        self.Creation_fichier_comptes(date_debut=date_debut, date_fin=date_fin, dict_familles=dict_familles)

        # Génération du fichier des factures
        # Le queryset (et non une liste) est transmis pour que le filtre des prestations soit une sous-requête
        factures = Facture.objects.filter(date_edition__gte=date_debut, date_edition__lte=date_fin, etat__isnull=True).order_by("pk")
        details_factures = self.Get_detail_factures(factures=factures)
        lignes = []
        for index_facture, facture in enumerate(factures, 1):
            code_famille, nom_famille = dict_familles.get(facture.famille_id, ("", ""))
            date_ecriture = facture.date_edition.strftime("%d%m%Y")

            # Ligne compte général
            index_ligne_detail = 0
            for index_ligne_detail, ligne_detail in enumerate(details_factures.get(facture, []), 1):
                lignes.append({
                    "num_ecriture": index_facture,
                    "num_ligne_ecriture": index_ligne_detail,
                    "date_ecriture": date_ecriture,
                    "compte_general": ligne_detail["code_compta"],
                    "compte_analytique": ligne_detail["code_analytique"],
                    "code_journal": "VE",
                    "type_piece": "FV",
                    "num_piece": "",
                    "montant": "%.2f" % -ligne_detail["montant"],
                    "libelle": ligne_detail["label"], # ou facture.famille.nom
                    "date_echeance": facture.date_echeance.strftime("%d%m%Y") if facture.date_echeance else "",
                    "num_reglement": "",
                    "num_facture": facture.numero,
                })

            # Ligne compte client
            lignes.append({
                "num_ecriture": index_facture,
                "num_ligne_ecriture": index_ligne_detail + 1,
                "date_ecriture": date_ecriture,
                "compte_general": code_famille,
                "compte_analytique": "",
                "code_journal": "VE",
                "type_piece": "FV",
                "num_piece": "",
                "montant": "%.2f" % facture.total,
                "libelle": nom_famille,
                "num_reglement": "",
                "num_facture": facture.numero,
            })
        self.Ecrire_fichier(nom_fichier="FAC", format_export=format_export_fac, lignes=lignes)

        # Génération du fichier des règlements
        depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")

        # Numéro de facture associé à chaque règlement
        ventilations = Ventilation.objects.filter(reglement__depot__in=depots, prestation__facture__isnull=False).values_list("reglement_id", "prestation__facture__numero")
        dict_reglements_factures = {idreglement: numero for idreglement, numero in ventilations}

        # Lecture de tous les règlements des dépôts en une seule requête
        dict_reglements_depots = {}
        reglements = Reglement.objects.filter(depot__in=depots).order_by("depot_id", "pk").values_list(
            "pk", "depot_id", "famille_id", "numero_piece", "montant", "mode__code_journal", "payeur__nom", "emetteur__nom")
        for reglement in reglements:
            dict_reglements_depots.setdefault(reglement[1], []).append(reglement)

        lignes = []
        for index_depot, depot in enumerate(depots, 1):
            date_ecriture = depot.date.strftime("%d%m%Y")

            # Ligne du règlement
            index_reglement = 0
            code_journal = ""
            for index_reglement, (idreglement, iddepot, idfamille, numero_piece, montant, code_journal_mode, nom_payeur, nom_emetteur) in enumerate(dict_reglements_depots.get(depot.pk, []), 1):
                code_famille, nom_famille = dict_familles.get(idfamille, ("", ""))
                code_journal = code_journal_mode or ""
                lignes.append({
                    "num_ecriture": index_depot,
                    "num_ligne_ecriture": index_reglement,
                    "date_ecriture": date_ecriture,
                    "compte_general": code_famille,
                    "code_journal": code_journal,
                    "type_piece": "FV",
                    "num_piece": numero_piece or "",
                    "montant": "%.2f" % -montant,
                    "libelle_ecriture": nom_famille,
                    "num_reglement": depot.pk,
                    "num_facture": dict_reglements_factures.get(idreglement, ""),
                    "emetteur": nom_payeur,
                    "etablissement_bancaire": nom_emetteur or "",
                    "monnaie": "E",
                })

            # Ligne du dépôt
            lignes.append({
                "num_ecriture": index_depot,
                "num_ligne_ecriture": index_reglement + 1,
                "date_ecriture": date_ecriture,
                "compte_general": depot.code_compta,
                "code_journal": code_journal,
                "type_piece": "FV",
                "montant": "%.2f" % (depot.montant or 0.0),
                "libelle_ecriture": depot.nom,
                "num_reglement": depot.pk,
            })
        self.Ecrire_fichier(nom_fichier="RGL", format_export=format_export_rgl, lignes=lignes)

        return True
