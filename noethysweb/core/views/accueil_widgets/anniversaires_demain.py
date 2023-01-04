# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views.accueil_widgets import anniversaires


class Widget(anniversaires.Widget):
    code = "anniversaires_demain"
    label = "Anniversaires du lendemain"

    def init_context_data(self):
        self.context['anniversaires_demain'] = self.Get_anniversaires(demain=True)
