# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Facture


class View(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/facturation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Facturation"
        context['liste_factures'] = Facture.objects.filter(famille=self.request.user.famille).order_by("-date_edition")
        context['liste_factures_impayees'] = [facture.solde_actuel for facture in Facture.objects.filter(famille=self.request.user.famille, solde_actuel__gt=0)]
        return context
