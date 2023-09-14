# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from decimal import Decimal
from core.utils import utils_dates
from django.utils.html import format_html
from django.urls import reverse_lazy, reverse



class Colonne():
    def __init__(self, code="", label="", classe="CharField", label_filtre=""):
        self.code = code
        self.label = label
        self.classe = classe
        self.label_filtre = label_filtre


class CustomDatatable():
    def __init__(self, colonnes=[], lignes=[], filtres=[]):
        self.colonnes = colonnes
        self.lignes = lignes

        # Filtrage
        if filtres:
            lignes_temp = []
            dict_colonnes = self.Get_dict_colonnes()
            for ligne in self.lignes:
                valide = True
                for filtre in filtres:
                    champ = filtre["champ"]
                    condition = filtre["condition"]
                    criteres = filtre["criteres"]

                    if champ in dict_colonnes:
                        colonne = dict_colonnes[champ]

                        # Valeur à étudier
                        valeur = ligne[colonne.index]

                        # Conversion
                        if colonne.classe == "DecimalField":
                            try:
                                valeur = Decimal(valeur)
                            except:
                                valeur = 0
                            criteres = [Decimal(critere) for critere in criteres]

                        if colonne.classe == "FloatField":
                            valeur = float(valeur)
                            criteres = [float(critere) for critere in criteres]

                        if colonne.classe == "IntegerField":
                            valeur = int(valeur)
                            criteres = [int(critere) for critere in criteres]

                        if colonne.classe == "DateField":
                            valeur = utils_dates.ConvertDateENGtoDate(valeur)
                            criteres = [utils_dates.ConvertDateENGtoDate(critere) for critere in criteres]

                        if colonne.classe == "BooleanField":
                            valeur = True if valeur in (True, "True") else False

                        # Comparaison
                        if condition == "EGAL" and not valeur == criteres[0]: valide = False
                        if condition == "DIFFERENT" and not valeur != criteres[0]: valide = False
                        if condition == "SUPERIEUR" and not valeur > criteres[0]: valide = False
                        if condition == "INFERIEUR" and not valeur < criteres[0]: valide = False
                        if condition == "SUPERIEUR_EGAL" and not valeur >= criteres[0]: valide = False
                        if condition == "INFERIEUR_EGAL" and not valeur <= criteres[0]: valide = False
                        if condition == "CONTIENT" and criteres[0] not in valeur: valide = False
                        if condition == "NE_CONTIENT_PAS" and criteres[0] not in valeur: valide = False
                        if condition == "COMPRIS" and not (criteres[0] <= valeur <= criteres[1]): valide = False
                        if condition == "VRAI" and not valeur == True: valide = False
                        if condition == "FAUX" and not valeur == False: valide = False

                if valide:
                    lignes_temp.append(ligne)

            self.lignes = lignes_temp

    def Get_dict_colonnes(self):
        dict_colonnes = {}
        for index, colonne in enumerate(self.colonnes):
            colonne.index = index
            dict_colonnes[colonne.code] = colonne
        return dict_colonnes


class ColonneAction:
    def __init__(self):
        self.liste_boutons = []

    def Ajouter(self, url=None, title="", image=""):
        if image == "modifier": image = "fa-pencil"
        if image == "imprimer": image = "fa-file-pdf-o"
        if image == "ouvrir": image = "fa-folder-open-o"
        if image == "famille": image = "fa-users"
        bouton = """<a type='button' class='btn btn-default btn-sm' href='%s' title='%s'><i class="fa %s"></i></a>""" % (url, title, image)
        self.liste_boutons.append(bouton)

    def Render(self):
        return format_html("&nbsp;".join(self.liste_boutons))

    def __str__(self):
        return self.Render()

