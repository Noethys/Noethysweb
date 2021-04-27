# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from portail.views.base import CustomView


class Accueil(CustomView, TemplateView):
    template_name = "portail/accueil.html"
    menu_code = "accueil"

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context['page_titre'] = "Accueil"
        return context
