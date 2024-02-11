# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, random
logger = logging.getLogger(__name__)
from django.core.cache import cache
from core.views import accueil_widget
from core.utils import utils_parametres
from core.data.data_astuces import LISTE_ASTUCES


class Widget(accueil_widget.Widget):
    code = "astuce"
    label = "Astuce du jour"

    def init_context_data(self):
        self.context["astuce"] = self.Get_astuce()

    def Get_astuce(self):
        num_astuce = cache.get("num_astuce")
        if not num_astuce:
            parametre = utils_parametres.Get(nom="num_astuce", categorie="page_accueil", valeur="")
            if parametre.startswith(str(datetime.date.today())):
                num_astuce = int(parametre.split(";")[1])
            else:
                num_astuce = random.randint(0, len(LISTE_ASTUCES) - 1)
                utils_parametres.Set(nom="num_astuce", categorie="page_accueil", valeur="%s;%d" % (datetime.date.today(), num_astuce))
            cache.set("num_astuce", num_astuce)
        return LISTE_ASTUCES[num_astuce]
