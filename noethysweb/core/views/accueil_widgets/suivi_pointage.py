# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from consommations.views import suivi_pointage


class Widget(accueil_widget.Widget):
    code = "suivi_pointage"
    label = "Suivi du pointage"

    def init_context_data(self):
        self.context["dict_pointage"] = suivi_pointage.Get_pointage(self.request)
