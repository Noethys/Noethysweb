# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


import logging, datetime, xlrd, csv
logger = logging.getLogger(__name__)
from core.models import Famille, Utilisateur
from core.utils import utils_db
from fiche_famille.utils import utils_internet


class Ligne():
    def __init__(self, dict_donnees={}):
        # Mémorisation des valeurs sous forme d'attributs
        [setattr(self, key, valeur) for key, valeur in dict_donnees.items()]


class Importer:
    def __init__(self):
        pass

    def Formate_telephone(self, tel=""):
        if not tel:
            return None
        tel_final = "{0}{1}.{2}{3}.{4}{5}.{6}{7}.{8}{9}.".format(*[x for x in tel if x in "0123456789"])
        return tel_final

    def Formate_date(self, date, classeur):
        if date:
            return datetime.datetime(*xlrd.xldate_as_tuple(date, classeur.datemode)).date()
        return None

    def Get_data_classeur(self, nom_fichier=""):
        dict_feuilles = {}
        classeur = xlrd.open_workbook(nom_fichier)
        for num_feuille in range(0, classeur.nsheets):
            feuille = classeur.sheet_by_index(num_feuille)
            dict_noms_colonnes = {}
            liste_lignes = []
            for num_ligne in range(0, feuille.nrows):
                valeurs_ligne = {}
                for num_colonne in range(0, feuille.ncols):
                    valeur = feuille.cell(rowx=num_ligne, colx=num_colonne).value
                    if num_ligne == 0:
                        dict_noms_colonnes[num_colonne] = valeur
                    else:
                        valeurs_ligne[dict_noms_colonnes[num_colonne]] = valeur
                if valeurs_ligne:
                    liste_lignes.append(valeurs_ligne)
            dict_feuilles[feuille.name] = liste_lignes
        return dict_feuilles, classeur

    def Get_data_csv(self, nom_fichier=""):
        lignes = []
        with open(nom_fichier, encoding="utf-8") as fichier:
            for ligne in csv.DictReader(fichier, delimiter=";"):
                lignes.append(Ligne(dict_donnees=ligne))
        return lignes

    def Creer_famille(self):
        # Création d'une famille
        famille = Famille.objects.create()
        logger.debug("Création de la famille ID%d" % famille.pk)
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
        return famille

    def Maj_infos(self):
        """ Mise à jour de toutes les infos familles et individus """
        utils_db.Maj_infos()

    def Start(self):
        pass


def Importer_tout():
    importer = Importer()
    importer.Start()
    print("Importation terminée")
