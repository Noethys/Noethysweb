# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.views import accueil_widget


class Widget(accueil_widget.Widget):
    code = "messages"
    label = "Messages"

    def init_context_data(self):
        pass
