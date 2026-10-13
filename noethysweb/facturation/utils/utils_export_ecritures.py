# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, uuid
from django.conf import settings
from core.models import Prestation, Facture


class BaseExporter():
    def __init__(self, request=None, options=None):
        self.options = options
        self.request = request
        self.erreurs = []

    def Generer(self):
        pass

    def Generer_xlsx(self, nom_fichier=None):
        # Création du répertoire de sortie et des fichiers
        nom_rep = "export_xlsx_ecritures"
        self.Creer_repertoire_sortie(nom_rep=nom_rep)

        import xlsxwriter
        classeur = xlsxwriter.Workbook(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_rep, nom_fichier))
        if not self.Creation_fichier(classeur=classeur):
            return False

        return os.path.join(settings.MEDIA_URL, self.rep_base, nom_rep, nom_fichier).replace("\\", "/")

    def Creation_fichier(self, classeur=None):
        return True

    def Creer_repertoire_sortie(self, nom_rep=""):
        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_rep)
        os.makedirs(self.rep_destination)

    def Get_detail_factures(self, factures=[]):
        """ Renvoie le détail des prestations regroupées par facture : {facture: [{label, code_compta, code_analytique, montant}, ...]} """
        # Lecture des seuls champs utiles en une requête (évite d'instancier et de déchiffrer les individus)
        prestations = Prestation.objects.filter(facture__in=factures).values_list(
            "facture_id", "label", "montant", "code_compta", "code_analytique",
            "activite__code_comptable", "activite__code_analytique",
            "cotisation__type_cotisation__code_comptable", "cotisation__type_cotisation__code_analytique")

        dict_resultats = {}
        for idfacture, label, montant, code_compta_prestation, code_analytique_prestation, code_compta_activite, code_analytique_activite, code_compta_cotisation, code_analytique_cotisation in prestations:
            # Recherche le code compta et le code analytique
            code_compta = code_compta_prestation or code_compta_cotisation or code_compta_activite or None
            code_analytique = code_analytique_prestation or code_analytique_cotisation or code_analytique_activite or None

            # Mémorisation
            key = (label, code_compta, code_analytique)
            dict_facture = dict_resultats.setdefault(idfacture, {})
            dict_facture[key] = dict_facture.get(key, 0) + montant

        # Les résultats sont indexés par facture
        dict_factures = {facture.pk: facture for facture in factures}
        dict_resultats2 = {}
        for idfacture, dict_facture in dict_resultats.items():
            liste = [{"label": label, "code_compta": code_compta, "code_analytique": code_analytique, "montant": montant} for (label, code_compta, code_analytique), montant in dict_facture.items()]
            liste.sort(key=lambda x: x["label"])
            dict_resultats2[dict_factures.get(idfacture) or Facture(pk=idfacture)] = liste

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
        colonnes = [(code_colonne, taille_colonne) for code_colonne, nom_colonne, taille_colonne in format_export]
        return "\n".join(["".join([str(valeurs_ligne.get(code_colonne, "") or "")[:taille_colonne].ljust(taille_colonne) for code_colonne, taille_colonne in colonnes]) for valeurs_ligne in lignes])
