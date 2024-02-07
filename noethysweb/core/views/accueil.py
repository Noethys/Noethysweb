# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, importlib
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.conf import settings
from core.views.base import CustomView
from outils.utils import utils_update


class Accueil(CustomView, TemplateView):
    template_name = "core/accueil/accueil.html"
    menu_code = "accueil"

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context['page_titre'] = "Accueil"

        # Technique
        context['mode_demo'] = settings.MODE_DEMO
        context['nouvelle_version'] = utils_update.Get_update_for_accueil(request=self.request)
        context['super_utilisateur'] = self.request.user.is_superuser

        # Configuration accueil
        context['configuration_accueil'] = json.loads(context["options_interface"]["configuration_accueil"])
        liste_widgets = []
        for ligne in context['configuration_accueil']:
            for colonne in ligne:
                for item in colonne[1:]:
                    liste_widgets.append(item)

        # Importation des widgets
        for nom_widget in liste_widgets:
            try:
                module = importlib.import_module("core.views.accueil_widgets.%s" % nom_widget)
                widget = module.Widget(request=self.request, context=context)
                widget.init_context_data()
            except:
                pass

        return context
