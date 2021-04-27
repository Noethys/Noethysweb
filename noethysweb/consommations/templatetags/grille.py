#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.template.defaulttags import register


# @register.simple_tag
# def get_inscription_from_dict(individu=None, activite=None, dict_inscriptions_by_individu={}):
#     for inscription in dict_inscriptions_by_individu.get(individu, []):
#         if inscription.activite == activite:
#             return inscription
#     return None

@register.simple_tag
def get_groupe(selection_inscriptions={}, inscription=None):
    if not inscription:
        return None
    if not selection_inscriptions or selection_inscriptions == "__all__" or inscription.pk not in selection_inscriptions:
        return inscription.groupe_id
    return selection_inscriptions[inscription.pk]

@register.simple_tag
def get_liste_individus_coches(data={}):
    liste_individus = []
    for key_individu, inscriptions in data["dict_inscriptions_by_individu"].items():
        liste_individus.append(key_individu)
    return liste_individus