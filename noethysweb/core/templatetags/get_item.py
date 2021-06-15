#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.template.defaulttags import register
from django.db import models
from django.utils.safestring import mark_safe
from core.utils import utils_dates
from core.utils import utils_preferences
import os, re

@register.filter
def get_item(dictionary, key):
    if key not in dictionary:
        return None
    return dictionary.get(key)

@register.filter
def est_en_vacances(date, liste_vacances):
    return utils_dates.EstEnVacances(date, liste_vacances)

@register.filter
def is_in_list(valeur, liste_str):
    if isinstance(liste_str, str):
        liste_str = liste_str.split(";")
    return valeur in liste_str

@register.filter
def montant(valeur):
    if not valeur: valeur = 0.0
    return "%0.2f %s" % (valeur, utils_preferences.Get_symbole_monnaie())

@register.filter
def somme(liste):
    return sum(liste)

@register.filter
def basename(nom_fichier):
    return os.path.basename(nom_fichier)

@register.simple_tag
def creation_string_key(*args):
    """ Convertit une liste d'arguments en une chaîne avec des valeurs séparées par les tirets bas. Ex : 'abcd_1_2_3' """
    liste_temp = []
    for valeur in args:
        # Si c'est un model, on prend la pk
        if isinstance(valeur, models.Model):
            valeur = valeur.pk
        liste_temp.append(str(valeur))
    return "_".join(liste_temp)

@register.simple_tag
def creation_string_key2(*args):
    """ Convertit une liste d'arguments en une chaîne avec des valeurs séparées par les points-virgule. Ex : 'abcd;1;2;3' """
    liste_temp = []
    for valeur in args:
        # Si c'est un model, on prend la pk
        if isinstance(valeur, models.Model):
            valeur = valeur.pk
        liste_temp.append(str(valeur))
    return ";".join(liste_temp)

@register.filter
def surligner(texte, expression):
    pattern = re.compile(re.escape(expression), re.IGNORECASE)
    try:
        return mark_safe(pattern.sub('<span class="surlignage">\g<0></span>', texte))
    except:
        return texte

@register.filter
def verbose_name(value):
    return value._meta.verbose_name

@register.filter
def verbose_name_plural(value):
    return value._meta.verbose_name_plural

@register.filter
def startswith(texte, chaine):
    if isinstance(texte, str):
        return texte.startswith(chaine)
    return False

@register.filter
def is_date_in_inscription(inscription, date):
    return inscription.Is_date_in_inscription(date)

@register.simple_tag
def get_item_defaut(dictionnaire, key, defaut=None):
    return dictionnaire.get(key, defaut)
