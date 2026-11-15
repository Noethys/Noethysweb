# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget
from collaborateurs.utils import utils_accueil


class Widget(accueil_widget.Widget):
    code = "collaborateurs_equipe_du_jour"
    label = "Collaborateurs : équipe du jour"

    def init_context_data(self):
        # Le widget n'est pas affiché si l'utilisateur n'a pas accès à la fonctionnalité
        if not self.request.user.has_perm("core.planning_equipe"):
            return
        self.context["collaborateurs_equipe_du_jour"] = utils_accueil.Get_equipe_du_jour(user=self.request.user)
        self.context["collaborateurs_equipe_du_jour_selecteur"] = utils_accueil.Selecteur_date(context=self.context, code_widget=self.code, id_champ="collaborateurs_equipe_date")
