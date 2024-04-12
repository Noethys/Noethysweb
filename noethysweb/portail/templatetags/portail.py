# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.template.defaulttags import register
from portail.utils import utils_approbations


@register.filter
def get_etat_certification(date_certification=None, duree_certification=None):
    return utils_approbations.Get_etat_certification(date_certification, duree_certification)
