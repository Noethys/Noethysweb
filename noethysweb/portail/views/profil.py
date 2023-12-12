# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from portail.views.base import CustomView


class View(CustomView, TemplateView):
    menu_code = "portail_accueil"
    template_name = "portail/profil.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Paramètres du compte")
        context['box_titre'] = _("Profil de l'utilisateur")
        context['box_introduction'] = ""
        return context
