# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Individu, Rattachement
from core.utils import utils_dates, utils_import_excel


def Importer(nom_fichier=""):
    """ Import CSV uniquement """
    importation = Import()
    importation.Start(nom_fichier=nom_fichier)


class Import(utils_import_excel.Importer):
    def Start(self, nom_fichier=""):
        lignes = self.Get_data_csv(nom_fichier)

        # Regroupement des enfants par famille
        dict_data_temp = {}
        for ligne in lignes:
            dict_data_temp.setdefault(ligne.Famille_Identifiant, [])
            dict_data_temp[ligne.Famille_Identifiant].append(ligne)

        # Création de chaque famille
        for Famille_Identifiant, liste_enfants in dict_data_temp.items():
            for index, ligne in enumerate(liste_enfants):

                # Création de la famille
                if index == 0:
                    famille = self.Creer_famille()

                    # Création du payeur
                    if ligne.Responsable_1_Nom:
                        payeur = Individu.objects.create(
                            civilite=1 if ligne.Responsable_1_Civilite == "M" else 3,
                            nom=ligne.Responsable_1_Nom.upper(),
                            prenom=ligne.Responsable_1_Prenom.strip().title(),
                            rue_resid=ligne.Responsable_1_Adresse.title() if ligne.Responsable_1_Adresse.strip() else None,
                            cp_resid=str(ligne.Responsable_1_Code_postal) if ligne.Responsable_1_Code_postal else None,
                            ville_resid=ligne.Responsable_1_Ville.strip().upper() if ligne.Responsable_1_Ville else None,
                            tel_domicile=self.Formate_telephone(ligne.Responsable_1_Telephone.strip()),
                            tel_mobile=self.Formate_telephone(ligne.Responsable_1_Portable.strip()),
                            travail_tel=self.Formate_telephone(ligne.Responsable_1_TelPro.strip()),
                            mail=ligne.Responsable_1_Mail.strip(),
                        )
                        Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=payeur)
                        logger.debug("Création payeur : %s" % payeur)

                    # Création du conjoint
                    if ligne.Responsable_2_Nom:
                        conjoint = Individu.objects.create(
                            civilite=1 if ligne.Responsable_2_Civilite == "M" else 3,
                            nom=ligne.Responsable_2_Nom.upper(),
                            prenom=ligne.Responsable_2_Prenom.strip().title(),
                            rue_resid=ligne.Responsable_2_Adresse.title() if ligne.Responsable_2_Adresse.strip() else None,
                            cp_resid=str(ligne.Responsable_2_Code_postal) if ligne.Responsable_2_Code_postal else None,
                            ville_resid=ligne.Responsable_2_Ville.strip().upper() if ligne.Responsable_2_Ville else None,
                            tel_domicile=self.Formate_telephone(ligne.Responsable_2_Telephone.strip()),
                            tel_mobile=self.Formate_telephone(ligne.Responsable_2_Portable.strip()),
                            travail_tel=self.Formate_telephone(ligne.Responsable_2_TelPro.strip()),
                            mail=ligne.Responsable_2_Mail.strip(),
                        )
                        Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=conjoint)
                        logger.debug("Création conjoint : %s" % conjoint)

                # Création de l'enfant
                individu = Individu.objects.create(
                    civilite=4 if ligne.Enfant_Civilite == "M" else 5,
                    nom=ligne.Enfant_Nom.strip().upper(),
                    prenom=ligne.Enfant_Prenom.title().strip(),
                    date_naiss=utils_dates.ConvertDateFRtoDate(ligne.Enfant_Date_de_naissance) if ligne.Enfant_Date_de_naissance else None,
                    adresse_auto=payeur.pk if ligne.Responsable_1_Nom else conjoint.pk,
                )
                Rattachement.objects.create(categorie=2, titulaire=False, famille=famille, individu=individu)
                logger.debug("Création enfant : %s" % individu)

        # Maj des infos familles
        self.Maj_infos()
