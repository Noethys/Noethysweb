# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from core.utils import utils_preferences

def ResolveurCalcul(texte="", dictValeurs={}):
    """ Pour résoudre les calculs """
    resultat = ""
    resultat_monetaire = False
    symbole_monnaie = utils_preferences.Get_symbole_monnaie()
    # Remplacement des valeurs
    for motcle, valeur in dictValeurs.items():
        if motcle in texte:
            # Conversion de la valeur
            if symbole_monnaie in valeur:
                resultat_monetaire = True

            for caract in " %sabcdefghijklmnopqrstuvwxyzéè-_" % symbole_monnaie:
                valeur = valeur.replace(caract, "")
                valeur = valeur.replace(caract.upper(), "")

            # Remplacement des valeurs
            texte = texte.replace(motcle, valeur)

    # Réalisation du calcul
    try:
        resultat = eval(texte)
        if resultat_monetaire == True:
            resultat = "%.02f %s" % (resultat, symbole_monnaie)
        else:
            resultat = str(resultat)
    except:
        pass

    return resultat


def ResolveurFormule(formule="", listeChamps=[], dictValeurs={}):
    """ Permet de résoudre une formule """
    formule = formule.rstrip("]]")
    formule = formule.lstrip("[[")
    # Recherche les infos dans la formule
    regex = re.compile(r"[^SI]({.+})(<>|>=|<=|>|<|=)(.*)->(.*)", re.S)
    resultat = regex.search(formule)
    if resultat == None or len(resultat.groups()) != 4:
        # Si aucune formule conditionnelle trouvée, regarde si c'est un calcul à effectuer
        resultat = ResolveurCalcul(texte=formule, dictValeurs=dictValeurs)
        return resultat

    # Formule conditionnelle
    champ, operateur, condition, valeur = resultat.groups()

    # Recherche une condition avec " OU "
    listeConditions = condition.split(" OU ")

    # Recherche la solution
    if champ in dictValeurs:
        valeurChamp = dictValeurs[champ]

        if valeurChamp == None:
            valeurChamp = ""

        # Comparaison des valeurs
        try:
            if operateur == "=":
                if valeurChamp == condition: return valeur
            if operateur == ">":
                if valeurChamp > condition: return valeur
            if operateur == "<":
                if valeurChamp < condition: return valeur
            if operateur == "<>":
                if valeurChamp != condition: return valeur
            if operateur == ">=":
                if valeurChamp >= condition: return valeur
            if operateur == "<=":
                if valeurChamp <= condition: return valeur
            if operateur == "=" and len(listeConditions) > 0:
                if valeurChamp in listeConditions: return valeur
        except:
            return ""

    # Renvoie la formule si elle n'a pas été résolue
    return ""


def DetecteFormule(texte):
    regex = re.compile(r"\[\[.*?\]\]", re.S)
    resultat = regex.findall(texte)
    return resultat


def ResolveurTexte(texte=u"", listeChamps=[], dictValeurs={}):
    formules = DetecteFormule(texte)
    # Si aucune formule trouvée
    if len(formules) == 0: return texte
    # On recherche la solution d'une formule
    for formule in formules:
        solution = ResolveurFormule(formule, listeChamps, dictValeurs)
        texte = texte.replace(formule, solution)
    return texte