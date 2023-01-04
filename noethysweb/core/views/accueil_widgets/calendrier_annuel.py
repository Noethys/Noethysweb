# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget


class Widget(accueil_widget.Widget):
    code = "calendrier_annuel"
    label = "Calendrier annuel"

    def init_context_data(self):
        pass
