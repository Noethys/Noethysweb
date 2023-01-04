# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from individus.views import suivi_inscriptions


class Widget(accueil_widget.Widget):
    code = "suivi_inscriptions"
    label = "Suivi des inscriptions"

    def init_context_data(self):
        self.context['suivi_inscriptions_parametres'] = suivi_inscriptions.Get_parametres(request=self.request)
