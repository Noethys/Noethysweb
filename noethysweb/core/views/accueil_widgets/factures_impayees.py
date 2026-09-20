# -*- coding: utf-8 -*-
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from core.utils import utils_factures_impayees


class Widget(accueil_widget.Widget):
    code = "factures_impayees"
    label = "Factures impayées"

    def init_context_data(self):
        self.context.update(utils_factures_impayees.Get_donnees(self.request))
