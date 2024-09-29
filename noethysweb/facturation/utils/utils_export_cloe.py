# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, datetime, shutil, uuid
from django.conf import settings
from core.models import Famille, Facture, Prestation, Depot, Reglement, Ventilation
from core.utils import utils_dates


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


class Exporter():
    def __init__(self, request=None, options=None):
        self.options = options
        self.request = request
        self.erreurs = []

    def Generer(self):
        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, "cloe")
        os.makedirs(self.rep_destination)

        # Création des fichiers
        if not self.Creation_fichiers():
            return False

        # Création du fichier ZIP
        nom_fichier_zip = "export_cloe_%s.zip" % datetime.date.today().strftime("%Y-%m-%d")
        shutil.make_archive(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier_zip.replace(".zip", "")), "zip", self.rep_destination)
        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier_zip)

    def Get_detail_factures(self, factures=[]):
        prestations = Prestation.objects.select_related("activite", "individu", "facture", "cotisation", "cotisation__type_cotisation").filter(facture__in=factures)

        dict_resultats = {}
        for prestation in prestations:
            # Recherche le code compta et le code analytique
            code_compta = None
            code_analytique = None
            if prestation.activite:
                if prestation.activite.code_comptable: code_compta = prestation.activite.code_comptable
                if prestation.activite.code_analytique: code_analytique = prestation.activite.code_analytique
            if hasattr(prestation, "cotisation"):
                if prestation.cotisation.type_cotisation.code_comptable: code_compta = prestation.cotisation.type_cotisation.code_comptable
                if prestation.cotisation.type_cotisation.code_analytique: code_analytique = prestation.cotisation.type_cotisation.code_analytique
            if prestation.code_compta: code_compta = prestation.code_compta
            if prestation.code_analytique: code_analytique = prestation.code_analytique

            # Mémorisation
            key = (prestation.label, code_compta, code_analytique)
            dict_resultats.setdefault(prestation.facture, {})
            dict_resultats[prestation.facture].setdefault(key, 0)
            dict_resultats[prestation.facture][key] += prestation.montant

        dict_resultats2 = {}
        for facture, dict_facture in dict_resultats.items():
            dict_resultats2.setdefault(facture, [])
            for (label, code_compta, code_analytique), montant in dict_facture.items():
                dict_resultats2[facture].append({"label": label, "code_compta": code_compta, "code_analytique": code_analytique, "montant": montant})
            dict_resultats2[facture].sort(key=lambda x: x["label"])

        return dict_resultats2

    def Get_erreurs_html(self):
        html = """
            <div class='text-red'>Les erreurs suivantes ont été rencontrées :<div><ul class='mt-2'>%s</ul>
            <div class="buttonHolder">
                <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                    <button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-times margin-r-5'></i>Fermer</button>
                </div>
            </div>
        """ % "".join(["<li>%s</li>" % erreur for erreur in self.erreurs])
        return html

    def Generer_fichier_texte(self, format_export=None, lignes=[]):
        texte = []
        for valeurs_ligne in lignes:
            ligne = []
            for code_colonne, nom_colonne, taille_colonne in format_export:
                valeur = str(valeurs_ligne.get(code_colonne, "") or "")
                ligne.append(valeur[:taille_colonne].ljust(taille_colonne))
            texte.append("".join(ligne))
        return "\n".join(texte)

    def Creation_fichiers(self):
        # Récupération de la période
        date_debut = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(self.options["periode"].split(";")[1])

        # Génération du fichier des comptes auxiliaires
        lignes = []
        for famille in Famille.objects.all().order_by("nom"):
            ligne = {}
            ligne["num_compte"] = "FAM%06d" % famille.pk
            if famille.code_compta:
                ligne["num_compte"] = famille.code_compta
            ligne["nom"] = famille.nom
            lignes_rue = famille.rue_resid.split("\n") if famille.rue_resid else []
            ligne["adresse"] = lignes_rue[0] if lignes_rue else ""
            ligne["complement_adresse"] = lignes_rue[1] if len(lignes_rue) > 1 else ""
            ligne["cp"] = famille.cp_resid
            ligne["ville"] = famille.ville_resid
            ligne["compte_collectif"] = self.options["compte_collectif"] or ""
            lignes.append(ligne)

        # Création du fichier
        texte = self.Generer_fichier_texte(format_export=format_export_cpt, lignes=lignes)
        with open(os.path.join(self.rep_destination, "CPT-%s.TXT" % datetime.date.today().strftime("%d%m%Y")), "w") as fichier:
            fichier.write(texte)

        # Génération du fichier des factures
        factures = Facture.objects.select_related("famille").filter(date_edition__gte=date_debut, date_edition__lte=date_fin).order_by("pk")
        details_factures = self.Get_detail_factures(factures=factures)
        lignes = []
        for index_facture, facture in enumerate(factures, 1):

            # Ligne compte général
            for index_ligne_detail, ligne_detail in enumerate(details_factures.get(facture, []), 1):
                ligne = {}
                ligne["num_ecriture"] = index_facture
                ligne["num_ligne_ecriture"] = index_ligne_detail
                ligne["date_ecriture"] = facture.date_edition.strftime("%d%m%Y")
                ligne["compte_general"] = ligne_detail["code_compta"]
                ligne["compte_analytique"] = ligne_detail["code_analytique"]
                ligne["code_journal"] = "VE"
                ligne["type_piece"] = "FV"
                ligne["num_piece"] = ""
                ligne["montant"] = "%.2f" % -ligne_detail["montant"]
                ligne["libelle"] = ligne_detail["label"] # ou facture.famille.nom
                ligne["date_echeance"] = facture.date_echeance.strftime("%d%m%Y") if facture.date_echeance else ""
                ligne["num_reglement"] = ""
                ligne["num_facture"] = facture.numero
                lignes.append(ligne)

            # Ligne compte client
            ligne = {}
            ligne["num_ecriture"] = index_facture
            ligne["num_ligne_ecriture"] = index_ligne_detail + 1
            ligne["date_ecriture"] = facture.date_edition.strftime("%d%m%Y")
            ligne["compte_general"] = facture.famille.code_compta or "FAM%06d" % facture.famille.pk
            ligne["compte_analytique"] = ""
            ligne["code_journal"] = "VE"
            ligne["type_piece"] = "FV"
            ligne["num_piece"] = ""
            ligne["montant"] = "%.2f" % facture.solde
            ligne["libelle"] = facture.famille.nom
            ligne["num_reglement"] = ""
            ligne["num_facture"] = facture.numero
            lignes.append(ligne)

        # Création du fichier
        texte = self.Generer_fichier_texte(format_export=format_export_fac, lignes=lignes)
        with open(os.path.join(self.rep_destination, "FAC-%s.TXT" % datetime.date.today().strftime("%d%m%Y")), "w") as fichier:
            fichier.write(texte)

        # Génération du fichier des règlements
        depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk")

        ventilations = Ventilation.objects.select_related("reglement", "prestation", "prestation__facture").filter(reglement__depot__in=depots, prestation__facture__isnull=False)
        dict_reglements_factures = {ventilation.reglement: ventilation.prestation.facture.numero for ventilation in ventilations}

        lignes = []
        for index_depot, depot in enumerate(depots, 1):

            # Ligne du règlement
            index_reglement = 0
            dernier_reglement = None
            for index_reglement, reglement in enumerate(Reglement.objects.select_related("famille", "mode", "emetteur", "payeur").filter(depot=depot), 1):
                dernier_reglement = reglement
                ligne = {}
                ligne["num_ecriture"] = index_depot
                ligne["num_ligne_ecriture"] = index_reglement
                ligne["date_ecriture"] = depot.date.strftime("%d%m%Y")
                ligne["compte_general"] = reglement.famille.code_compta or "FAM%06d" % reglement.famille.pk
                ligne["code_journal"] = reglement.mode.code_journal or ""
                ligne["type_piece"] = "FV"
                ligne["num_piece"] = reglement.numero_piece or ""
                ligne["montant"] = "%.2f" % -reglement.montant
                ligne["libelle_ecriture"] = reglement.famille.nom
                ligne["num_reglement"] = depot.pk
                ligne["num_facture"] = dict_reglements_factures.get(reglement, "")
                ligne["emetteur"] = reglement.payeur.nom
                ligne["etablissement_bancaire"] = reglement.emetteur.nom if reglement.emetteur else ""
                ligne["monnaie"] = "E"
                lignes.append(ligne)

            # Ligne du dépôt
            ligne = {}
            ligne["num_ecriture"] = index_depot
            ligne["num_ligne_ecriture"] = index_reglement + 1
            ligne["date_ecriture"] = depot.date.strftime("%d%m%Y")
            ligne["compte_general"] = depot.code_compta
            ligne["code_journal"] = dernier_reglement.mode.code_journal if dernier_reglement and dernier_reglement.mode.code_journal else ""
            ligne["type_piece"] = "FV"
            ligne["montant"] = "%.2f" % (depot.montant or 0.0)
            ligne["libelle_ecriture"] = depot.nom
            ligne["num_reglement"] = depot.pk
            lignes.append(ligne)

        # Création du fichier
        texte = self.Generer_fichier_texte(format_export=format_export_rgl, lignes=lignes)
        with open(os.path.join(self.rep_destination, "RGL-%s.TXT" % datetime.date.today().strftime("%d%m%Y")), "w") as fichier:
            fichier.write(texte)

        return True
