# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Famille, Individu, Rattachement, Utilisateur
from core.utils import utils_db
from fiche_famille.utils import utils_internet


def Importer(nom_fichier=""):
    Import(nom_fichier)


class Import():
    def __init__(self, nom_fichier=""):
        import xlrd
        self.classeur = xlrd.open_workbook(nom_fichier)
        self.feuille = self.classeur.sheet_by_index(0)

        for num_ligne in range(1, self.feuille.nrows-1):

            # Création de la famille
            famille = Famille.objects.create()
            logger.debug("Création de la famille ID%d" % famille.pk)

            # Création et enregistrement des codes pour le portail
            internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
            internet_mdp, date_expiration_mdp = utils_internet.CreationMDP()
            famille.internet_identifiant = internet_identifiant
            famille.internet_mdp = internet_mdp
            utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=True, date_expiration_mdp=date_expiration_mdp)
            utilisateur.save()
            utilisateur.set_password(internet_mdp)
            utilisateur.save()
            famille.utilisateur = utilisateur
            famille.save()

            # Création des responsables
            for type_individu in ("pere", "mere"):
                info_individu = self.Get_valeur(num_ligne, 1 if type_individu == "pere" else 2)
                info_adresse = self.Get_valeur(num_ligne, 4 if type_individu == "pere" else 5)
                info_telephones = self.Get_valeur(num_ligne, 7 if type_individu == "pere" else 8)
                telephones = {}
                for tel in info_telephones:
                    if "Pro" in tel:telephones["travail_tel"] = self.Formate_telephone(tel)
                    if ": 06" in tel: telephones["tel_mobile"] = self.Formate_telephone(tel)
                    if ": 07" in tel: telephones["tel_mobile"] = self.Formate_telephone(tel)
                    if ": 02" in tel: telephones["tel_domicile"] = self.Formate_telephone(tel)

                if info_individu[0]:
                    individu = Individu.objects.create(
                        civilite=1 if type_individu == "pere" else 3,
                        nom=info_individu[0].strip(),
                        prenom=info_individu[1].strip().title(),
                        rue_resid=info_adresse[0].strip().title() if info_adresse[0].strip() else None,
                        cp_resid=info_adresse[1].strip() if info_adresse[1] else None,
                        ville_resid=info_adresse[2].strip() if info_adresse[2] else None,
                        tel_domicile=telephones.get("tel_domicile", None),
                        tel_mobile=telephones.get("tel_mobile", None),
                        travail_tel=telephones.get("travail_tel", None),
                        mail=info_individu[2].strip() if len(info_individu) > 2 else None,
                    )
                    Rattachement.objects.create(categorie=1, titulaire=True, famille=famille, individu=individu)
                    logger.debug("Création individu : %s" % individu)

        # Mise à jour de toutes les infos familles et individus
        utils_db.Maj_infos()

    def Formate_telephone(self, tel=""):
        try:
            tel_final = "{0}{1}.{2}{3}.{4}{5}.{6}{7}.{8}{9}.".format(*[x for x in tel[tel.find(":"):] if x in "0123456789"])
        except:
            tel_final = None
        return tel_final

    def Get_valeur(self, num_ligne=None, num_colonne=None):
        valeur = self.feuille.cell(rowx=num_ligne, colx=num_colonne).value
        return valeur.split("\n")
