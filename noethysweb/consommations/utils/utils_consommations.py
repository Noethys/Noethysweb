# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import LISTE_ETATS_CONSO

def Get_label_etat(etat="reservation"):
    for code, label in LISTE_ETATS_CONSO:
        if code == etat:
            return label
    return ""
