#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.template.defaulttags import register
from core.utils.utils_dates import LISTE_MOIS


@register.simple_tag
def group_by_mois(prestations=[], cle="mois"):
    dict_prestations = {}
    for prestation in prestations:
        if cle == "mois": key = ("%d_%d" % (prestation.date.year, prestation.date.month), "%s %d" % (LISTE_MOIS[prestation.date.month-1].capitalize(), prestation.date.year))
        if cle == "facture": key = (prestation.facture_id, ("Facture n°%s" % prestation.facture.numero) if prestation.facture else "Non facturé")
        if cle == "individu": key = (prestation.individu_id, prestation.individu)
        if cle == "date": key = (str(prestation.date), prestation.date)
        dict_prestations.setdefault(key, [])
        dict_prestations[key].append(prestation)
    return dict_prestations
