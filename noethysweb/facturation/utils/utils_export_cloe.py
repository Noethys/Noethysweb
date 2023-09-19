# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, calendar, datetime, shutil, uuid
from django.conf import settings
from core.models import Famille, Facture, Prestation, Depot, Reglement
from core.utils import utils_dates, utils_parametres, utils_texte
from dateutil.relativedelta import relativedelta


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
        prestations = Prestation.objects.select_related("activite", "individu", "facture").filter(facture__in=factures)

        dict_resultats = {}
        for prestation in prestations:
            # Recherche le code compta et le code analytique
            code_compta = None
            code_analytique = None
            if prestation.activite:
                if prestation.activite.code_comptable: code_compta = prestation.activite.code_comptable
                if prestation.activite.code_analytique: code_analytique = prestation.activite.code_analytique
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
            for nom_colonne, taille_colonne in format_export:
                valeur = str(valeurs_ligne.get(nom_colonne, "") or "")
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
            ligne["compte_collectif"] = "411000"
            lignes.append(ligne)

        # Création du fichier
        format_export = [("num_compte", 10), ("nom", 30), ("adresse", 30), ("complement_adresse", 30), ("cp", 5), ("ville", 44), ("compte_collectif", 10)]
        texte = self.Generer_fichier_texte(format_export=format_export, lignes=lignes)
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
        format_export = [("num_ecriture", 6), ("num_ligne_ecriture", 6), ("date_ecriture", 8), ("compte_general", 11), ("compte_analytique", 10), ("code_journal", 3),
                         ("type_piece", 3), ("num_piece", 15), ("montant", 15), ("libelle", 50), ("date_echeance", 8), ("num_reglement", 12), ("num_facture", 20)]
        texte = self.Generer_fichier_texte(format_export=format_export, lignes=lignes)
        with open(os.path.join(self.rep_destination, "FAC-%s.TXT" % datetime.date.today().strftime("%d%m%Y")), "w") as fichier:
            fichier.write(texte)

        # Génération du fichier des règlements
        lignes = []
        for index_depot, depot in enumerate(Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("pk"), 1):

            # Ligne du règlement
            for index_reglement, reglement in enumerate(Reglement.objects.select_related("famille", "emetteur").filter(depot=depot), 1):
                ligne = {}
                ligne["num_ecriture"] = index_depot
                ligne["num_ligne_ecriture"] = index_reglement
                ligne["date_depot"] = depot.date.strftime("%d%m%Y")
                ligne["num_compte"] = "FAM%06d" % reglement.famille.pk
                if reglement.famille.code_compta:
                    ligne["num_compte"] = reglement.famille.code_compta
                ligne["montant"] = "%.2f" % -reglement.montant
                ligne["nom"] = reglement.famille.nom
                ligne["type_piece"] = "FV"
                ligne["nom_emetteur"] = reglement.emetteur.nom if reglement.emetteur else ""
                ligne["monnaie"] = "E"
                lignes.append(ligne)

            # Ligne du dépôt
            ligne = {}
            ligne["num_ecriture"] = index_depot
            ligne["num_ligne_ecriture"] = index_reglement + 1
            ligne["date_depot"] = depot.date.strftime("%d%m%Y")
            ligne["num_compte"] = depot.code_compta
            ligne["montant"] = "%.2f" % depot.montant
            ligne["nom"] = depot.nom
            ligne["type_piece"] = "FV"
            lignes.append(ligne)

        # Création du fichier
        format_export = [("num_compte", 10), ("nom", 30), ("adresse", 30), ("complement_adresse", 30), ("cp", 5), ("ville", 44), ("compte_collectif", 10)]
        texte = self.Generer_fichier_texte(format_export=format_export, lignes=lignes)
        with open(os.path.join(self.rep_destination, "RGL-%s.TXT" % datetime.date.today().strftime("%d%m%Y")), "w") as fichier:
            fichier.write(texte)

        return True
