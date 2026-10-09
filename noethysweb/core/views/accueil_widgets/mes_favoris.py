# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views import accueil_widget, menu_favoris


class Widget(accueil_widget.Widget):
    code = "mes_favoris"
    label = "Mes favoris"

    def init_context_data(self):
        codes = menu_favoris.Get_codes_favoris(self.context.get("options_interface", {}))
        commandes = menu_favoris.Get_commandes_favorites(menu_principal=self.context.get("menu_principal", None), codes=codes)
        self.context["widget_favoris"] = [{
            "code": commande.code,
            "titre": commande.titre,
            "url": commande.GetUrl(),
            "icone": commande.icone,
            "nature": commande.nature,
            "description": commande.description,
            "menu": commande.GetMenuRacine().titre,
            "nouveau": commande.nouveau,
        } for commande in commandes]
