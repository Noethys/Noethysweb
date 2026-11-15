# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from collaborateurs.utils import utils_accueil


class Widget(accueil_widget.Widget):
    code = "collaborateurs_heures_declarees"
    label = "Collaborateurs : heures déclarées à valider"

    def init_context_data(self):
        # Le widget n'est pas affiché si l'utilisateur n'a pas accès à la fonctionnalité
        if not self.request.user.has_perm("core.heures_declarees_collaborateurs"):
            return
        self.context["collaborateurs_heures_declarees"] = utils_accueil.Get_heures_declarees(user=self.request.user)
