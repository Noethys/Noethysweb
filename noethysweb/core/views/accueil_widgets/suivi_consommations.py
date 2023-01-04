# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from consommations.views import suivi_consommations


class Widget(accueil_widget.Widget):
    code = "suivi_consommations"
    label = "Suivi des consommations"

    def init_context_data(self):
        self.context['suivi_consommations_parametres'] = suivi_consommations.Get_parametres(request=self.request)
