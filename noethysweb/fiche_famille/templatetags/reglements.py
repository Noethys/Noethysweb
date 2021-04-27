#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.template.defaulttags import register


@register.simple_tag
def group_by_mois(prestations=[], cle="mois"):
    dict_prestations = {}
    for prestation in prestations:
        if cle == "mois": key = "%d_%d" % (prestation.date.year, prestation.date.month)
        if cle == "facture": key = prestation.facture
        if cle == "individu": key = prestation.individu
        if cle == "date": key = prestation.date
        dict_prestations.setdefault(key, [])
        dict_prestations[key].append(prestation)
    return dict_prestations
