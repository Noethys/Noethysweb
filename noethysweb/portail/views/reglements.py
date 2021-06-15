# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Reglement


class View(CustomView, TemplateView):
    menu_code = "portail_reglements"
    template_name = "portail/reglements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Règlements"
        context['liste_reglements'] = Reglement.objects.select_related("mode", "depot").filter(famille=self.request.user.famille).order_by("-date")
        return context
