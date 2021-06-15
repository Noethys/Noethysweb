# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from core.utils import utils_preferences


def Convert_liste_to_texte_virgules(liste=[]):
    """ Convertit un liste ['a', 'b', 'c'] en un texte 'a, b et c' """
    if len(liste) == 0:
        return ""
    elif len(liste) == 1:
        return liste[0]
    else:
        return ", ".join(liste[:-1]) + " et " + liste[-1]

def Incrementer(texte=""):
    """ Incrémenter un numéro dans une chaîne """
    lastNum = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')
    m = lastNum.search(texte)
    if m:
        next = str(int(m.group(1))+1)
        start, end = m.span(1)
        texte = texte[:max(end-len(next), start)] + next + texte[end:]
    return texte

def Fusionner_motscles(texte, dict_motscles={}):
    for motcle, valeur in dict_motscles.items():
        texte = texte.replace(motcle, str(valeur))
    return texte

def Formate_montant(montant=0.0):
    return "%.02f %s" % (montant, utils_preferences.Get_symbole_monnaie())


def ConvertStrToListe(texte=None, siVide=[], separateur=";", typeDonnee="entier"):
    """ Convertit un texte "1;2;3;4" en [1, 2, 3, 4] """
    if texte == None or texte == "":
        return siVide
    listeResultats = []
    temp = texte.split(separateur)
    for ID in temp:
        if typeDonnee == "entier":
            ID = int(ID)
        listeResultats.append(ID)
    return listeResultats

def ConvertListeToStr(liste=[], separateur=";"):
    """ Convertit une liste en texte """
    if liste == None : liste = []
    return separateur.join([str(x) for x in liste])

