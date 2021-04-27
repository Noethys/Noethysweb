# -*- coding: utf-8 -*-


#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

def Grouper_par_attribut(liste=[], attribut=""):
    """ Regroupe une liste de models par un attribut donné """
    dict_resultats = {}
    for valeur in liste:
        if getattr(valeur, attribut):
            if getattr(valeur, attribut) not in dict_resultats:
                dict_resultats[getattr(valeur, attribut)] = []
            dict_resultats[getattr(valeur, attribut)].append(valeur)
    return dict_resultats


def DictionnaireImbrique(dictionnaire={}, cles=[], valeur=None):
    """ Création de dictionnaires imbriqués """
    if len(cles) == 0:
        return dictionnaire

    if (cles[0] in dictionnaire) == False:
        dictionnaire[cles[0]] = {}
    if len(cles) == 1:
        if dictionnaire[cles[0]] == {}: dictionnaire[cles[0]] = valeur
        return dictionnaire

    if (cles[1] in dictionnaire[cles[0]]) == False:
        dictionnaire[cles[0]][cles[1]] = {}
    if len(cles) == 2:
        if dictionnaire[cles[0]][cles[1]] == {}: dictionnaire[cles[0]][cles[1]] = valeur
        return dictionnaire

    if (cles[2] in dictionnaire[cles[0]][cles[1]]) == False:
        dictionnaire[cles[0]][cles[1]][cles[2]] = {}
    if len(cles) == 3:
        if dictionnaire[cles[0]][cles[1]][cles[2]] == {}: dictionnaire[cles[0]][cles[1]][cles[2]] = valeur
        return dictionnaire

    if (cles[3] in dictionnaire[cles[0]][cles[1]][cles[2]]) == False:
        dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]] = {}
    if len(cles) == 4:
        if dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]] == {}: dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]] = valeur
        return dictionnaire

    if (cles[4] in dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]]) == False:
        dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]] = {}
    if len(cles) == 5:
        if dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]] == {}: dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]] = valeur
        return dictionnaire

    if (cles[5] in dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]]) == False:
        dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]][cles[5]] = {}
    if len(cles) == 6:
        if dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]][cles[5]] == {}:
            dictionnaire[cles[0]][cles[1]][cles[2]][cles[3]][cles[4]][cles[5]] = valeur
        return dictionnaire

    return None
