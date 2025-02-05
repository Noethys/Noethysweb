# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, uuid
from django.conf import settings
from core.models import Prestation


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
