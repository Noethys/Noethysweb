# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, calendar, datetime, shutil, uuid
from django.conf import settings
from core.models import PesLot, PesPiece, Prestation, Organisateur, LISTE_MOIS
from core.utils import utils_parametres, utils_texte


class ExporterBase():
    def __init__(self, idlot=None, request=None, nom_fichier_simple="export.xml"):
        self.idlot = idlot
        self.request = request
        self.organisateur = Organisateur.objects.filter(pk=1).first()
        self.erreurs = []
        self.nom_fichier_simple = nom_fichier_simple

    def ConvertToTexte(self, valeur, majuscules=False):
        if majuscules and valeur:
            valeur = utils_texte.Supprimer_accents(valeur.upper())
        valeur = "%s" % valeur
        valeur = valeur.replace("\n", " ")
        valeur = valeur.replace("\r", " ")
        valeur = valeur.strip()
        return valeur

    def Generer(self):
        # Importation des données
        self.lot = PesLot.objects.select_related("modele", "modele__compte", "modele__mode").get(pk=self.idlot)
        self.pieces = PesPiece.objects.select_related("famille", "prelevement_mandat", "prelevement_mandat__individu", "titulaire_helios", "tiers_solidaire", "facture", "famille__titulaire_helios", "famille__tiers_solidaire").filter(lot=self.lot)

        # Calcul des dates extrêmes du mois du lot
        self.date_min_lot = datetime.date(self.lot.exercice, self.lot.mois, 1)
        self.date_max_lot = datetime.date(self.lot.exercice, self.lot.mois, calendar.monthrange(self.lot.exercice, self.lot.mois)[1])

        # Création du répertoire de sortie
        self.rep_base = os.path.join("temp", str(uuid.uuid4()))
        self.rep_destination = os.path.join(settings.MEDIA_ROOT, self.rep_base, self.code_format)
        os.makedirs(self.rep_destination)

        # Création des fichiers
        if not self.Creation_fichiers():
            return False

        # Renvoie le fichier à télécharger
        if self.code_format == "magnus":
            # Création du fichier ZIP
            nom_fichier_zip = self.lot.nom + ".zip"
            shutil.make_archive(os.path.join(settings.MEDIA_ROOT, self.rep_base, nom_fichier_zip.replace(".zip", "")), "zip", self.rep_destination)
            return os.path.join(settings.MEDIA_URL, self.rep_base, nom_fichier_zip)
        else:
            return os.path.join(settings.MEDIA_URL, self.rep_base, self.code_format, self.nom_fichier_simple)

    def Get_detail_pieces(self):
        prestations = Prestation.objects.select_related("activite", "individu", "facture").filter(facture_id__in=[piece.facture_id for piece in self.pieces])

        dict_resultats = {}
        dict_prestations_factures = {}
        liste_dates_prestations = []
        for prestation in prestations:

            # Recherche le code compta et le code prod local
            id_poste = self.lot.modele.id_poste
            code_prodloc = self.lot.modele.code_prodloc
            service1 = self.lot.modele.service1
            service2 = self.lot.modele.service2
            if prestation.activite:
                if prestation.activite.code_comptable: id_poste = prestation.activite.code_comptable
                if prestation.activite.code_produit_local: code_prodloc = prestation.activite.code_produit_local
                if prestation.activite.service1: service1 = prestation.activite.service1
                if prestation.activite.service2: service2 = prestation.activite.service2
            if prestation.code_compta: id_poste = prestation.code_compta
            if prestation.code_produit_local: code_prodloc = prestation.code_produit_local

            dict_prestations_factures.setdefault(prestation.facture, [])
            dict_prestations_factures[prestation.facture].append({
                "prestation": prestation, "label": prestation.label, "montant": prestation.montant, "id_poste": id_poste,
                "code_prodloc": code_prodloc, "service1": service1, "service2": service2,
            })

            # Définit le montant
            montant_unitaire = prestation.montant / prestation.quantite

            # Mémorise la date de la prestation
            if prestation.date not in liste_dates_prestations:
                liste_dates_prestations.append(prestation.date)

            # Définit le label
            libelle = self.lot.modele.prestation_libelle
            libelle = libelle.replace("{ACTIVITE_NOM}", prestation.activite.nom if prestation.activite else "")
            libelle = libelle.replace("{ACTIVITE_ABREGE}", prestation.activite.abrege if prestation.activite and prestation.activite.abrege else "")
            libelle = libelle.replace("{PRESTATION_LABEL}", prestation.label)
            libelle = libelle.replace("{PRESTATION_QUANTITE}", str(prestation.quantite))
            libelle = libelle.replace("{PRESTATION_MOIS}", {num: label for (num, label) in LISTE_MOIS}[prestation.date.month])
            libelle = libelle.replace("{PRESTATION_ANNEE}", str(prestation.date.year))
            libelle = libelle.replace("{INDIVIDU_PRENOM}", prestation.individu.prenom or prestation.individu.nom if prestation.individu else "")
            libelle = libelle.replace("{INDIVIDU_NOM}", prestation.individu.nom if prestation.individu and prestation.individu.nom else "")
            libelle = libelle.replace("{MOIS}", str(self.lot.mois))
            libelle = libelle.replace("{MOIS_LETTRES}", self.lot.get_mois_display())
            libelle = libelle.replace("{ANNEE}", str(self.lot.exercice))
            libelle = libelle.replace("{DATE_DEBUT_MOIS}", datetime.date(prestation.date.year, prestation.date.month, 1).strftime('%d/%m/%Y'))
            libelle = libelle.replace("{DATE_FIN_MOIS}", datetime.date(prestation.date.year, prestation.date.month, calendar.monthrange(prestation.date.year, prestation.date.month)[1]).strftime('%d/%m/%Y'))
            libelle = libelle.replace("{PRESTATION_DEBUT_MOIS}", datetime.date(prestation.date.year, prestation.date.month, 1).strftime('%d/%m/%Y'))
            libelle = libelle.replace("{PRESTATION_FIN_MOIS}", datetime.date(prestation.date.year, prestation.date.month, calendar.monthrange(prestation.date.year, prestation.date.month)[1]).strftime('%d/%m/%Y'))

            # Mémorisation du label et de la quantité
            libelle = (libelle, montant_unitaire)
            dict_resultats.setdefault(prestation.facture, {})
            dict_resultats[prestation.facture].setdefault(prestation.individu, {})
            dict_resultats[prestation.facture][prestation.individu].setdefault(libelle, 0)
            dict_resultats[prestation.facture][prestation.individu][libelle] += prestation.quantite

        dict_resultats2 = {}
        for facture, dict_facture in dict_resultats.items():
            dict_resultats2.setdefault(facture, [])
            for individu, dict_individu in dict_facture.items():
                for (libelle, montant), quantite in dict_individu.items():
                    dict_resultats2[facture].append({"libelle": libelle, "quantite": quantite, "montant": montant})
                dict_resultats2[facture].sort(key=lambda x: x["libelle"])

        # Mémorise les dates extrêmes des prestations
        self.prestation_date_min = min(liste_dates_prestations)
        self.prestation_date_max = max(liste_dates_prestations)

        return dict_resultats2, dict_prestations_factures

    def Get_dict_codes(self, dict_prestations_factures=None):
        # Recherche poste et code local
        dict_codes = {}
        for facture, liste_prestations in dict_prestations_factures.items():
            dict_codes.setdefault(facture, {})
            for dict_prestation in liste_prestations:
                key = (dict_prestation["id_poste"], dict_prestation["code_prodloc"], dict_prestation["service1"], dict_prestation["service2"])
                dict_codes[facture].setdefault(key, 0)
                dict_codes[facture][key] += dict_prestation["montant"]
        return dict_codes

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

    def Formate_libelle(self, texte="", piece=None):
        # Général
        texte = texte.replace("{NOM_ORGANISATEUR}", self.organisateur.nom)
        if piece:
            texte = texte.replace("{NUM_FACTURE}", str(piece.facture.numero))

        # Période du lot
        texte = texte.replace("{MOIS}", str(self.lot.mois))
        texte = texte.replace("{MOIS_LETTRES}", self.lot.get_mois_display())
        texte = texte.replace("{ANNEE}", str(self.lot.exercice))
        texte = texte.replace("{DATE_DEBUT_MOIS}", datetime.date(self.lot.exercice, self.lot.mois, 1).strftime('%d/%m/%Y'))
        texte = texte.replace("{DATE_FIN_MOIS}", datetime.date(self.lot.exercice, self.lot.mois, calendar.monthrange(self.lot.exercice, self.lot.mois)[1]).strftime('%d/%m/%Y'))

        # Période des prestations
        if hasattr(self, "prestation_date_min"):
            texte = texte.replace("{PRESTATION_DATE_MIN}", self.prestation_date_min.strftime("%d/%m/%Y"))
            texte = texte.replace("{PRESTATION_DATE_MAX}", self.prestation_date_max.strftime("%d/%m/%Y"))
            texte = texte.replace("{PRESTATION_DEBUT_MOIS}", datetime.date(self.prestation_date_min.year, self.prestation_date_min.month, 1).strftime("%d/%m/%Y"))
            texte = texte.replace("{PRESTATION_FIN_MOIS}", datetime.date(self.prestation_date_min.year, self.prestation_date_min.month, calendar.monthrange(self.prestation_date_min.year, self.prestation_date_min.month)[1]).strftime("%d/%m/%Y"))
            texte = texte.replace("{PRESTATION_MOIS}", {num: label for (num, label) in LISTE_MOIS}[self.prestation_date_min.month])
            texte = texte.replace("{PRESTATION_ANNEE}", str(self.prestation_date_min.year))

        return texte

    def Generation_pieces_jointes(self, repertoire=""):
        """ Génération des pièces jointes """
        dict_factures = {piece.facture_id: piece.facture for piece in self.pieces}

        # Création du répertoire
        repertoire_pj = os.path.join(self.rep_destination, "PJ")
        if not os.path.isdir(repertoire_pj):
            os.mkdir(repertoire_pj)

        # Récupération des options d'impression
        from facturation.forms.factures_options_impression import VALEURS_DEFAUT
        dict_options = utils_parametres.Get_categorie(categorie="impression_facture", utilisateur=self.request.user, parametres=VALEURS_DEFAUT)
        dict_options["modele"] = self.lot.modele.modele_document

        # Génération des factures du format PDF
        from facturation.utils import utils_facturation
        facturation = utils_facturation.Facturation()
        resultat = facturation.Impression(liste_factures=list(dict_factures.keys()), dict_options=dict_options, mode_email=True)
        if resultat == False:
            return False

        # Déplacement des PDF vers le répertoire PJ
        dict_pieces_jointes = {}
        for IDfacture, donnees in resultat["noms_fichiers"].items():
            NomPJ = "Facture_%s.pdf" % dict_factures[IDfacture].numero
            numero_facture = dict_factures[IDfacture].numero
            IdUnique = str(numero_facture)
            shutil.move(settings.MEDIA_ROOT + donnees["nom_fichier"], os.path.join(repertoire_pj, NomPJ))
            dict_pieces_jointes[IDfacture] = {"NomPJ": NomPJ, "IdUnique": IdUnique, "numero_facture": numero_facture}

        return dict_pieces_jointes

    def Creation_fichiers(self):
        """ A surcharger """
        pass
