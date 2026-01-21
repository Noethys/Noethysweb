# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Individu, Rattachement
from core.utils import utils_dates, utils_import_excel


def Importer(nom_fichier=""):
    """ nom fichier modèle : FACTU_EXPORT_639020130158717367 """
    importation = Import()
    importation.Start(nom_fichier=nom_fichier)


class Import(utils_import_excel.Importer):
    def Start(self, nom_fichier=""):
        data = self.Get_data_xlsx(nom_fichier, num_ligne_entete=0)

        # Regroupement des enfants par famille
        dict_data_temp = {}
        for nom_feuille, lignes in data.items():
            for ligne in lignes:
                key_payeur = "%s_%s_%s" % (ligne["Nom"], ligne["Prénom"], ligne["Adresse"])
                dict_data_temp.setdefault(key_payeur, {})
                dict_data_temp[key_payeur][ligne["ID Enfant"]] = ligne

        # Création de chaque famille
        for dict_lignes in dict_data_temp.values():
            ligne = list(dict_lignes.values())[0]

            # Création de la famille
            famille = self.Creer_famille()

            # Création du payeur
            payeur = Individu.objects.create(
                civilite=1 if ligne["Civilité Payeur"] == "M." else 3,
                nom=ligne["Nom Payeur"].upper(),
                prenom=ligne["Prénom Payeur"].strip().title(),
                rue_resid=ligne["Adresse Payeur"].title() if ligne["Adresse Payeur"].strip() else None,
                cp_resid=str(ligne["Code Postal Payeur"]) if ligne["Code Postal Payeur"] else None,
                ville_resid=ligne["Ville Payeur"].strip().upper() if ligne["Ville Payeur"] else None,
                tel_domicile=self.Formate_telephone(ligne["Téléphone Domicile"].strip()) if ligne["Prénom"] == ligne["Prénom Payeur"] else None,
                tel_mobile=self.Formate_telephone(ligne["Téléphone Portable"].strip()) if ligne["Prénom"] == ligne["Prénom Payeur"] else None,
                mail=ligne["Courriel"].strip() if ligne["Prénom"] == ligne["Prénom Payeur"] else None,
            )
            Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=payeur)
            logger.debug("Création payeur : %s" % payeur)

            # Création du conjoint
            if ligne["Prénom Payeur 2"]:
                conjoint = Individu.objects.create(
                    civilite=1 if ligne["Civilité Payeur 2"] == "M." else 3,
                    nom=ligne["Nom Payeur 2"].upper(),
                    prenom=ligne["Prénom Payeur 2"].strip().title(),
                    adresse_auto=payeur.pk,
                )
                Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=conjoint)
                logger.debug("Création conjoint : %s" % conjoint)

            # Création des enfants
            for ligne_enfant in dict_lignes.values():
                individu = Individu.objects.create(
                    civilite=4 if ligne_enfant["Enfant Sexe"] == "Garçon" else 5,
                    nom=ligne_enfant["Enfant Nom"].strip(),
                    prenom=ligne_enfant["Enfant Prénom"].title().strip(),
                    date_naiss=utils_dates.ConvertDateFRtoDate(ligne_enfant["Enfant Date Naissance"]) if ligne_enfant["Enfant Date Naissance"] else None,
                    adresse_auto=payeur.pk,
                )
                Rattachement.objects.create(categorie=2, titulaire=False, famille=famille, individu=individu)
                logger.debug("Création enfant : %s" % individu)

        # Maj des infos familles
        self.Maj_infos()
