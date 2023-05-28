# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from outils.views import suivi_reservations


class Widget(accueil_widget.Widget):
    code = "suivi_reservations"
    label = "Suivi des réservations"

    def init_context_data(self):
        self.context['suivi_reservations_parametres'] = suivi_reservations.Get_parametres(request=self.request)
