# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from comptabilite.views import suivi_achats


class Widget(accueil_widget.Widget):
    code = "suivi_achats"
    label = "Suivi des achats"

    def init_context_data(self):
        self.context["demandes_achats"] = suivi_achats.Get_achats(self.request)
