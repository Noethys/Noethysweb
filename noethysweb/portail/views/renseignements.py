# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Rattachement


class View(CustomView, TemplateView):
    menu_code = "portail_renseignements"
    template_name = "portail/renseignements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Renseignements"
        context['rattachements'] = Rattachement.objects.prefetch_related('individu').filter(famille=self.request.user.famille).order_by("individu__nom", "individu__prenom")
        return context
